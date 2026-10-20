// protects: Peer settings cannot poison frame writers, and disabled push cannot allocate streams.
// fails_when: Invalid settings mutate connection state or push permission differs from the initial wire settings.
// why_new: Ordinary response tests cannot inspect rejected settings or preserve upstream enabled-push behavior.
// seam: none
package http2

import (
	"bufio"
	"bytes"
	"fmt"
	"io"
	"net"
	"sync"
	"testing"
	"time"

	http "github.com/bogdanfinn/fhttp"
	"github.com/bogdanfinn/fhttp/http2/hpack"
)

func instagrapiSettingsFrame(t *testing.T, settings ...Setting) *SettingsFrame {
	t.Helper()
	var wire bytes.Buffer
	if err := NewFramer(&wire, nil).WriteSettings(settings...); err != nil {
		t.Fatal(err)
	}
	frame, err := NewFramer(nil, &wire).ReadFrame()
	if err != nil {
		t.Fatal(err)
	}
	return frame.(*SettingsFrame)
}

func instagrapiSettingsConn() (*ClientConn, *bytes.Buffer) {
	var wire bytes.Buffer
	cc := &ClientConn{
		t: &Transport{}, maxFrameSize: 16384, maxConcurrentStreams: 1000,
		initialWindowSize: 65535, streams: make(map[uint32]*clientStream),
	}
	cc.cond = sync.NewCond(&cc.mu)
	cc.bw = bufio.NewWriter(&wire)
	cc.fr = NewFramer(cc.bw, nil)
	cc.henc = hpack.NewEncoder(&cc.hbuf)
	cc.hencMaxTableSize = initialHeaderTableSize
	return cc, &wire
}

func TestInstagrapiRejectInvalidPeerSettingsBeforeMutation(t *testing.T) {
	for _, tc := range []struct {
		name    string
		setting Setting
		code    ErrCode
	}{
		{"zero_frame", Setting{SettingMaxFrameSize, 0}, ErrCodeProtocol},
		{"short_frame", Setting{SettingMaxFrameSize, 16383}, ErrCodeProtocol},
		{"oversize_frame", Setting{SettingMaxFrameSize, 1 << 24}, ErrCodeProtocol},
		{"invalid_push", Setting{SettingEnablePush, 2}, ErrCodeProtocol},
		{"invalid_connect", Setting{SettingEnableConnectProtocol, 2}, ErrCodeProtocol},
	} {
		t.Run(tc.name, func(t *testing.T) {
			cc, wire := instagrapiSettingsConn()
			frame := instagrapiSettingsFrame(t,
				Setting{SettingMaxConcurrentStreams, 7},
				Setting{SettingHeaderTableSize, 0}, tc.setting)
			err := (&clientConnReadLoop{cc: cc}).processSettings(frame)
			if err != ConnectionError(tc.code) {
				t.Fatalf("invalid setting %v: got %v, want connection error %v", tc.setting, err, tc.code)
			}
			if cc.maxFrameSize != 16384 || cc.maxConcurrentStreams != 1000 || cc.initialWindowSize != 65535 || cc.hencMaxTableSize != initialHeaderTableSize {
				t.Fatalf("invalid settings changed state: frame=%d concurrent=%d window=%d table=%d", cc.maxFrameSize, cc.maxConcurrentStreams, cc.initialWindowSize, cc.hencMaxTableSize)
			}
			if wire.Len() != 0 {
				t.Fatal("invalid peer settings were acknowledged")
			}
		})
	}
}

func TestInstagrapiAcceptValidPeerSettingsBoundaries(t *testing.T) {
	for _, size := range []uint32{16384, 1<<24 - 1} {
		for _, window := range []uint32{0, 1<<31 - 1} {
			t.Run(fmt.Sprintf("frame_%d_window_%d", size, window), func(t *testing.T) {
				cc, wire := instagrapiSettingsConn()
				frame := instagrapiSettingsFrame(t,
					Setting{SettingMaxFrameSize, size}, Setting{SettingInitialWindowSize, window},
					Setting{SettingID(0xffff), 0xffffffff})
				if err := (&clientConnReadLoop{cc: cc}).processSettings(frame); err != nil {
					t.Fatal(err)
				}
				if cc.maxFrameSize != size || cc.initialWindowSize != window {
					t.Fatalf("valid settings lost: frame=%d window=%d", cc.maxFrameSize, cc.initialWindowSize)
				}
				ack, err := NewFramer(nil, wire).ReadFrame()
				if err != nil {
					t.Fatal(err)
				}
				if settings, ok := ack.(*SettingsFrame); !ok || !settings.IsAck() {
					t.Fatalf("valid settings were not acknowledged: %T", ack)
				}
			})
		}
	}
}

type instagrapiPushHandler struct {
	requests chan *PushedRequest
	release  chan struct{}
}

func (h *instagrapiPushHandler) HandlePush(request *PushedRequest) {
	h.requests <- request
	<-h.release
}

func instagrapiPushConn(t *testing.T, transport *Transport) (*ClientConn, []Setting) {
	t.Helper()
	client, peer := net.Pipe()
	settings := make(chan []Setting, 1)
	peerDone := make(chan struct{})
	go func() {
		defer close(peerDone)
		preface := make([]byte, len(clientPreface))
		if _, err := io.ReadFull(peer, preface); err != nil || !bytes.Equal(preface, clientPreface) {
			return
		}
		frame, err := NewFramer(nil, peer).ReadFrame()
		if err != nil {
			return
		}
		if f, ok := frame.(*SettingsFrame); ok {
			var initial []Setting
			f.ForeachSetting(func(s Setting) error { initial = append(initial, s); return nil })
			settings <- initial
		}
		io.Copy(io.Discard, peer)
	}()
	client.SetWriteDeadline(time.Now().Add(time.Second))
	cc, err := transport.NewClientConn(client)
	if err != nil {
		client.Close()
		peer.Close()
		t.Fatal(err)
	}
	t.Cleanup(func() {
		cc.forgetStreamID(2)
		cc.Close()
		peer.Close()
		for _, done := range []<-chan struct{}{cc.readerDone, peerDone} {
			select {
			case <-done:
			case <-time.After(time.Second):
				t.Error("native peer goroutine did not stop")
			}
		}
	})
	select {
	case initial := <-settings:
		return cc, initial
	case <-time.After(time.Second):
		t.Fatal("native connection did not send its settings")
		return nil, nil
	}
}

func TestInstagrapiPushPermissionFollowsAdvertisedSettings(t *testing.T) {
	for _, tc := range []struct {
		name     string
		settings map[SettingID]uint32
		order    []SettingID
		allowed  bool
	}{
		{"explicit_disabled", map[SettingID]uint32{SettingEnablePush: 0}, []SettingID{SettingEnablePush}, false},
		{"explicit_enabled", map[SettingID]uint32{SettingEnablePush: 1}, []SettingID{SettingEnablePush}, true},
		{"handler_default_enabled", nil, nil, true},
		{"wire_default_enabled", map[SettingID]uint32{}, nil, true},
		{"unadvertised_map_value", map[SettingID]uint32{SettingEnablePush: 0}, nil, true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			handler := &instagrapiPushHandler{make(chan *PushedRequest, 1), make(chan struct{})}
			t.Cleanup(func() { close(handler.release) })
			transport := &Transport{Settings: tc.settings, SettingsOrder: tc.order, PushHandler: handler}
			cc, initial := instagrapiPushConn(t, transport)
			advertised := uint32(1) // RFC default when SETTINGS_ENABLE_PUSH is absent.
			for _, setting := range initial {
				if setting.ID == SettingEnablePush {
					advertised = setting.Val
				}
			}
			if (advertised == 1) != tc.allowed {
				t.Fatalf("wrong setup: actual wire settings %v", initial)
			}
			// Later map edits must not change what this connection advertised.
			transport.Settings = map[SettingID]uint32{SettingEnablePush: 1 - advertised}
			req, err := http.NewRequest("GET", "https://peer.invalid/original", nil)
			if err != nil {
				t.Fatal(err)
			}
			cc.mu.Lock()
			stream := cc.newStreamWithID(1, false)
			stream.req = req
			cc.mu.Unlock()
			promise := &MetaPushPromiseFrame{
				PushPromiseFrame: &PushPromiseFrame{FrameHeader: FrameHeader{StreamID: 1}, PromiseID: 2},
				Fields:           []hpack.HeaderField{{Name: ":method", Value: "GET"}, {Name: ":scheme", Value: "https"}, {Name: ":authority", Value: "peer.invalid"}, {Name: ":path", Value: "/pushed"}},
			}
			err = (&clientConnReadLoop{cc: cc}).processPushPromise(promise)
			if !tc.allowed {
				if err != ConnectionError(ErrCodeProtocol) {
					t.Fatalf("disabled push: got %v, want PROTOCOL_ERROR", err)
				}
				cc.mu.Lock()
				count, highest := len(cc.streams), cc.highestPromiseID
				cc.mu.Unlock()
				if count != 1 || highest != 0 || len(handler.requests) != 0 {
					t.Fatal("disabled push allocated a stream or invoked its handler")
				}
				return
			}
			if err != nil {
				t.Fatalf("advertised enabled push was rejected: %v", err)
			}
			select {
			case pushed := <-handler.requests:
				if pushed.Promise.URL.Path != "/pushed" || pushed.pushedStream.ID != 2 {
					t.Fatal("enabled push did not preserve the promised request")
				}
			case <-time.After(time.Second):
				t.Fatal("enabled push never reached its handler")
			}
		})
	}
}

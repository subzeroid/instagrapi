// protects: Failed native construction leaves no cached nil client and nil cleanup remains safe.
// fails_when: CreateClient registers a failed client or RemoveSession panics on a nil cache entry.
// why_new: Response-level Python fixtures cannot establish the actual native cache construction invariant.
// seam: none
package tls_client_cffi_src

import "testing"

func TestInstagrapiFailedConstructionDoesNotCacheNil(t *testing.T) {
	id, badProxy := "instagrapi-construction-fixture", "%"
	t.Cleanup(func() { clientsLock.Lock(); delete(clients, id); clientsLock.Unlock() })
	_, _, _, err := CreateClient(RequestInput{SessionId: &id, ProxyUrl: &badProxy, TLSClientIdentifier: "chrome_120", DisableHttp3: true})
	if err == nil {
		t.Fatal("invalid proxy must reject client construction")
	}
	if _, err := GetClient(id); err == nil {
		t.Fatal("failed construction retained a native cache entry")
	}
}

func TestInstagrapiRemoveNilCacheEntryIsSafe(t *testing.T) {
	id := "instagrapi-nil-fixture"
	t.Cleanup(func() { clientsLock.Lock(); delete(clients, id); clientsLock.Unlock() })
	clientsLock.Lock()
	clients[id] = nil
	clientsLock.Unlock()
	defer func() {
		if recover() != nil {
			t.Fatal("nil cache cleanup must not panic")
		}
	}()
	RemoveSession(id)
	if _, err := GetClient(id); err == nil {
		t.Fatal("nil cache entry was not removed")
	}
}

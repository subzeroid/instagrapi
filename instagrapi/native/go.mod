module instagrapi-utls-native

go 1.26.0

require (
	github.com/bogdanfinn/fhttp v0.6.9
	github.com/bogdanfinn/tls-client v1.16.0
	github.com/google/uuid v1.6.0
)

require (
	github.com/andybalholm/brotli v1.2.0 // indirect
	github.com/bdandy/go-errors v1.2.2 // indirect
	github.com/bdandy/go-socks4 v1.2.3 // indirect
	github.com/bogdanfinn/quic-go-utls v1.0.10-utls // indirect
	github.com/bogdanfinn/utls v1.7.8-barnius // indirect
	github.com/bogdanfinn/websocket v1.5.6-barnius // indirect
	github.com/cloudflare/circl v1.6.3 // indirect
	github.com/klauspost/compress v1.18.7 // indirect
	github.com/quic-go/qpack v0.6.0 // indirect
	github.com/tam7t/hpkp v0.0.0-20160821193359-2b70b4024ed5 // indirect
	golang.org/x/crypto v0.57.0 // indirect
	golang.org/x/net v0.60.0 // indirect
	golang.org/x/sys v0.48.0 // indirect
	golang.org/x/text v0.42.0 // indirect
)

replace github.com/bogdanfinn/tls-client => ./tls-client

replace github.com/bogdanfinn/fhttp => ./fhttp

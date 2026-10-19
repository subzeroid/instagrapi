package main

/*
#include <stdlib.h>
*/
import "C"

import (
	"encoding/json"
	"fmt"
	"net/url"
	"sync"
	"unsafe"

	http "github.com/bogdanfinn/fhttp"
	tls_client_cffi_src "github.com/bogdanfinn/tls-client/cffi_src"
	"github.com/google/uuid"
)

var (
	unsafePointers    = make(map[string]*C.char)
	unsafePointersLck = sync.Mutex{}
)

//export freeMemory
func freeMemory(responseId *C.char) {
	responseIdString := C.GoString(responseId)

	unsafePointersLck.Lock()
	defer unsafePointersLck.Unlock()

	ptr, ok := unsafePointers[responseIdString]

	if !ok {
		return
	}

	C.free(unsafe.Pointer(ptr))

	delete(unsafePointers, responseIdString)
}

//export destroyAll
func destroyAll() *C.char {
	tls_client_cffi_src.ClearSessionCache()

	out := tls_client_cffi_src.DestroyOutput{
		Id:      uuid.New().String(),
		Success: true,
	}

	jsonResponse, marshallError := json.Marshal(out)

	if marshallError != nil {
		clientErr := tls_client_cffi_src.NewTLSClientError(marshallError)

		return handleErrorResponse("", false, clientErr)
	}

	responseString := C.CString(string(jsonResponse))

	unsafePointersLck.Lock()
	unsafePointers[out.Id] = responseString
	unsafePointersLck.Unlock()

	return responseString
}

//export destroySession
func destroySession(destroySessionParams *C.char) *C.char {
	destroySessionParamsJson := C.GoString(destroySessionParams)

	destroySessionInput := tls_client_cffi_src.DestroySessionInput{}
	marshallError := json.Unmarshal([]byte(destroySessionParamsJson), &destroySessionInput)

	if marshallError != nil {
		clientErr := tls_client_cffi_src.NewTLSClientError(marshallError)

		return handleErrorResponse("", false, clientErr)
	}

	tls_client_cffi_src.RemoveSession(destroySessionInput.SessionId)

	out := tls_client_cffi_src.DestroyOutput{
		Id:      uuid.New().String(),
		Success: true,
	}

	jsonResponse, marshallError := json.Marshal(out)

	if marshallError != nil {
		clientErr := tls_client_cffi_src.NewTLSClientError(marshallError)

		return handleErrorResponse(destroySessionInput.SessionId, true, clientErr)
	}

	responseString := C.CString(string(jsonResponse))

	unsafePointersLck.Lock()
	unsafePointers[out.Id] = responseString
	unsafePointersLck.Unlock()

	return responseString
}

//export getCookiesFromSession
func getCookiesFromSession(getCookiesParams *C.char) *C.char {
	getCookiesParamsJson := C.GoString(getCookiesParams)

	cookiesInput := tls_client_cffi_src.GetCookiesFromSessionInput{}
	marshallError := json.Unmarshal([]byte(getCookiesParamsJson), &cookiesInput)

	if marshallError != nil {
		clientErr := tls_client_cffi_src.NewTLSClientError(marshallError)

		return handleErrorResponse("", false, clientErr)
	}

	tlsClient, err := tls_client_cffi_src.GetClient(cookiesInput.SessionId)
	if err != nil {
		clientErr := tls_client_cffi_src.NewTLSClientError(err)

		return handleErrorResponse(cookiesInput.SessionId, true, clientErr)
	}

	u, parsErr := url.Parse(cookiesInput.Url)
	if parsErr != nil {
		clientErr := tls_client_cffi_src.NewTLSClientError(parsErr)

		return handleErrorResponse(cookiesInput.SessionId, true, clientErr)
	}

	cookies := tlsClient.GetCookies(u)

	out := tls_client_cffi_src.CookiesFromSessionOutput{
		Id:      uuid.New().String(),
		Cookies: transformCookies(cookies),
	}

	jsonResponse, marshallError := json.Marshal(out)

	if marshallError != nil {
		clientErr := tls_client_cffi_src.NewTLSClientError(marshallError)

		return handleErrorResponse(cookiesInput.SessionId, true, clientErr)
	}

	responseString := C.CString(string(jsonResponse))

	unsafePointersLck.Lock()
	unsafePointers[out.Id] = responseString
	unsafePointersLck.Unlock()

	return responseString
}

//export addCookiesToSession
func addCookiesToSession(addCookiesParams *C.char) *C.char {
	addCookiesParamsJson := C.GoString(addCookiesParams)

	cookiesInput := tls_client_cffi_src.AddCookiesToSessionInput{}
	marshallError := json.Unmarshal([]byte(addCookiesParamsJson), &cookiesInput)

	if marshallError != nil {
		clientErr := tls_client_cffi_src.NewTLSClientError(marshallError)

		return handleErrorResponse("", false, clientErr)
	}

	tlsClient, err := tls_client_cffi_src.GetClient(cookiesInput.SessionId)
	if err != nil {
		clientErr := tls_client_cffi_src.NewTLSClientError(err)

		return handleErrorResponse(cookiesInput.SessionId, true, clientErr)
	}

	u, parsErr := url.Parse(cookiesInput.Url)
	if parsErr != nil {
		clientErr := tls_client_cffi_src.NewTLSClientError(parsErr)

		return handleErrorResponse(cookiesInput.SessionId, true, clientErr)
	}

	tlsClient.SetCookies(u, buildCookies(cookiesInput.Cookies))

	allCookies := tlsClient.GetCookies(u)

	out := tls_client_cffi_src.CookiesFromSessionOutput{
		Id:      uuid.New().String(),
		Cookies: transformCookies(allCookies),
	}

	jsonResponse, marshallError := json.Marshal(out)

	if marshallError != nil {
		clientErr := tls_client_cffi_src.NewTLSClientError(marshallError)

		return handleErrorResponse(cookiesInput.SessionId, true, clientErr)
	}

	responseString := C.CString(string(jsonResponse))

	unsafePointersLck.Lock()
	unsafePointers[out.Id] = responseString
	unsafePointersLck.Unlock()

	return responseString
}

//export request
func request(requestParams *C.char) *C.char {
	requestParamsJson := C.GoString(requestParams)

	requestInput := tls_client_cffi_src.RequestInput{}
	marshallError := json.Unmarshal([]byte(requestParamsJson), &requestInput)

	if marshallError != nil {
		clientErr := tls_client_cffi_src.NewTLSClientError(marshallError)

		return handleErrorResponse("", false, clientErr)
	}

	tlsClient, sessionId, withSession, err := tls_client_cffi_src.CreateClient(requestInput)
	if err != nil {
		return handleErrorResponse(sessionId, withSession, err)
	}

	req, err := tls_client_cffi_src.BuildRequest(requestInput)
	if err != nil {
		clientErr := tls_client_cffi_src.NewTLSClientError(err)

		return handleErrorResponse(sessionId, withSession, clientErr)
	}

	cookies := buildCookies(requestInput.RequestCookies)

	if tlsClient.GetCookieJar() != nil && len(cookies) > 0 {
		tlsClient.SetCookies(req.URL, cookies)
	} else {
		for _, cookie := range cookies {
			req.AddCookie(cookie)
		}
	}

	resp, reqErr := tlsClient.Do(req)

	if reqErr != nil {
		clientErr := tls_client_cffi_src.NewTLSClientError(fmt.Errorf("failed to do request: %w", reqErr))

		return handleErrorResponse(sessionId, withSession, clientErr)
	}

	if resp == nil {
		clientErr := tls_client_cffi_src.NewTLSClientError(fmt.Errorf("response is nil"))

		return handleErrorResponse(sessionId, withSession, clientErr)
	}

	targetCookies := tlsClient.GetCookies(resp.Request.URL)

	response, err := tls_client_cffi_src.BuildResponse(sessionId, withSession, resp, targetCookies, requestInput)
	if err != nil {
		return handleErrorResponse(sessionId, withSession, err)
	}

	jsonResponse, marshallError := json.Marshal(response)

	if marshallError != nil {
		clientErr := tls_client_cffi_src.NewTLSClientError(marshallError)

		return handleErrorResponse(sessionId, withSession, clientErr)
	}

	responseString := C.CString(string(jsonResponse))

	unsafePointersLck.Lock()
	unsafePointers[response.Id] = responseString
	unsafePointersLck.Unlock()

	return responseString
}

func handleErrorResponse(sessionId string, withSession bool, err *tls_client_cffi_src.TLSClientError) *C.char {
	response := tls_client_cffi_src.Response{
		Id:      uuid.New().String(),
		Status:  0,
		Body:    err.Error(),
		Headers: nil,
		Cookies: nil,
	}

	if withSession {
		response.SessionId = sessionId
	}

	jsonResponse, marshallError := json.Marshal(response)

	if marshallError != nil {
		errStr := C.CString(marshallError.Error())

		return errStr
	}

	responseString := C.CString(string(jsonResponse))

	unsafePointersLck.Lock()
	unsafePointers[response.Id] = responseString
	unsafePointersLck.Unlock()

	return responseString
}

func buildCookies(cookies []tls_client_cffi_src.Cookie) []*http.Cookie {
	var ret []*http.Cookie

	for _, cookie := range cookies {
		ret = append(ret, &http.Cookie{
			Name:     cookie.Name,
			Value:    cookie.Value,
			Path:     cookie.Path,
			Domain:   cookie.Domain,
			Expires:  cookie.Expires.Time,
			MaxAge:   cookie.MaxAge,
			Secure:   cookie.Secure,
			HttpOnly: cookie.HttpOnly,
		})
	}

	return ret
}

func transformCookies(cookies []*http.Cookie) []tls_client_cffi_src.Cookie {
	var ret []tls_client_cffi_src.Cookie

	for _, cookie := range cookies {
		ret = append(ret, tls_client_cffi_src.Cookie{
			Name:     cookie.Name,
			Value:    cookie.Value,
			Path:     cookie.Path,
			Domain:   cookie.Domain,
			MaxAge:   cookie.MaxAge,
			Secure:   cookie.Secure,
			HttpOnly: cookie.HttpOnly,
			Expires: tls_client_cffi_src.Timestamp{
				Time: cookie.Expires,
			},
		})
	}

	return ret
}

func main() {
}

//export instagrapiNativeABI
func instagrapiNativeABI() C.int { return 1 }

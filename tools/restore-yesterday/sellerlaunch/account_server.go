package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

func accountHandler(root string) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/api/seller-login", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodOptions {
			return
		}
		var body struct {
			Phone string `json:"phone"`
		}
		if err := readJSON(r, &body); err != nil {
			writeAccountError(w, http.StatusBadRequest, errBadPhone)
			return
		}
		status, password, err := issueLogin(root, body.Phone)
		if err != nil {
			writeAccountError(w, http.StatusBadRequest, err)
			return
		}
		writeAccountJSON(w, map[string]string{"status": status, "password": password})
	})
	mux.HandleFunc("/api/seller-enter", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodOptions {
			return
		}
		var body struct {
			Phone    string `json:"phone"`
			Password string `json:"password"`
		}
		if err := readJSON(r, &body); err != nil {
			writeAccountError(w, http.StatusBadRequest, errBadPhone)
			return
		}
		if err := enterLogin(root, body.Phone, body.Password); err != nil {
			status := http.StatusBadRequest
			if errors.Is(err, errBadPassword) {
				status = http.StatusUnauthorized
			}
			writeAccountError(w, status, err)
			return
		}
		writeAccountJSON(w, map[string]bool{"ok": true})
	})
	mux.HandleFunc("/api/seller-status", func(w http.ResponseWriter, r *http.Request) {
		writeAccountJSON(w, map[string]string{"phone": activePhone(root)})
	})
	mux.HandleFunc("/api/seller-logout", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodOptions {
			return
		}
		if err := logoutLogin(root); err != nil {
			writeAccountError(w, http.StatusBadRequest, err)
			return
		}
		writeAccountJSON(w, map[string]bool{"ok": true})
	})
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		w.Header().Set("Access-Control-Allow-Private-Network", "true")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		mux.ServeHTTP(w, r)
	})
}

func sellerLoginPortList() []int {
	return []int{8790, 8791, 8792, 8793, 8794, 8795, 18790, 28790, 9876, 18081, 29170}
}

func startAccountServer(root string) error {
	_, err := listenAccount(root, sellerLoginPortList())
	return err
}

func listenAccount(root string, ports []int) (int, error) {
	var reasons []string
	for _, port := range ports {
		listener, err := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", port))
		if err != nil {
			reasons = append(reasons, err.Error())
			continue
		}
		go (&http.Server{Handler: accountHandler(root)}).Serve(listener)
		_ = writeLoginPort(root, port)
		return port, nil
	}
	for _, port := range ports {
		if accountServing(fmt.Sprintf("http://127.0.0.1:%d/api/seller-status", port)) {
			_ = writeLoginPort(root, port)
			return port, nil
		}
	}
	if len(reasons) == 0 {
		return 0, errors.New("로그인 포트를 열지 못했습니다.")
	}
	return 0, errors.New(strings.Join(reasons, "\n"))
}

func writeLoginPort(root string, port int) error {
	payload := []byte(strconv.Itoa(port))
	paths := []string{
		filepath.Join(root, "seller-login-port.txt"),
		filepath.Join(root, "_internal", "app", "static", "seller-login-port.txt"),
		filepath.Join(root, "app", "static", "seller-login-port.txt"),
	}
	var first error
	wrote := false
	for _, path := range paths {
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			if first == nil {
				first = err
			}
			continue
		}
		if err := os.WriteFile(path, payload, 0o644); err != nil {
			if first == nil {
				first = err
			}
			continue
		}
		wrote = true
	}
	if !wrote && first != nil {
		return first
	}
	return nil
}

func accountServing(rawURL string) bool {
	client := &http.Client{Timeout: 700 * time.Millisecond}
	resp, err := client.Get(rawURL)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}

func ensureAccountServer(root string) error {
	var err error
	for attempt := 0; attempt < 3; attempt++ {
		if _, err = listenAccount(root, sellerLoginPortList()); err == nil {
			return nil
		}
		time.Sleep(400 * time.Millisecond)
	}
	return err
}

func readJSON(r *http.Request, dest any) error {
	defer r.Body.Close()
	data, err := io.ReadAll(io.LimitReader(r.Body, 1<<16))
	if err != nil {
		return err
	}
	return json.Unmarshal(data, dest)
}

func writeAccountJSON(w http.ResponseWriter, body any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	_ = json.NewEncoder(w).Encode(body)
}

func writeAccountError(w http.ResponseWriter, status int, err error) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
}

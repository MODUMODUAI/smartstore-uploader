package main

import (
	"encoding/json"
	"errors"
	"io"
	"net"
	"net/http"
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

func startAccountServer(root string) error {
	listener, err := net.Listen("tcp", "127.0.0.1:8790")
	if err != nil {
		return err
	}
	server := &http.Server{Handler: accountHandler(root)}
	go server.Serve(listener)
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
	err := startAccountServer(root)
	if err == nil {
		return nil
	}
	if accountServing("http://127.0.0.1:8790/api/seller-status") {
		return nil
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

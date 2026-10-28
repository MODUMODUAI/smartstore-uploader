package main

import (
	"errors"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestIssuedPasswordOpensSameData(t *testing.T) {
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, "data"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "data", "products.txt"), []byte("alpha"), 0o644); err != nil {
		t.Fatal(err)
	}
	status, password, err := issueLogin(root, "010-1234-5678")
	if err != nil || status != "new" || password == "" {
		t.Fatalf("issue %s %s %v", status, password, err)
	}
	again, same, err := issueLogin(root, "01012345678")
	if err != nil || again != "new" || same != password {
		t.Fatalf("pending %s %s %v", again, same, err)
	}
	if err := enterLogin(root, "01012345678", strings.ToLower(password[:4]+" "+password[4:])); err != nil {
		t.Fatal(err)
	}
	got, err := os.ReadFile(filepath.Join(root, "data", "products.txt"))
	if err != nil || string(got) != "alpha" {
		t.Fatalf("first phone data %q %v", got, err)
	}
	if activePhone(root) != "01012345678" {
		t.Fatal(activePhone(root))
	}
	exists, next, err := issueLogin(root, "01012345678")
	if err != nil || exists != "exists" || next != "" {
		t.Fatalf("after enter %s %q %v", exists, next, err)
	}
	if err := enterLogin(root, "01012345678", "WRONG"); !errors.Is(err, errBadPassword) {
		t.Fatal(err)
	}
	status, password, err = issueLogin(root, "01099998888")
	if err != nil || status != "new" {
		t.Fatal(err)
	}
	if err := enterLogin(root, "01099998888", password); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(root, "data", "products.txt")); !os.IsNotExist(err) {
		t.Fatal("second phone saw the first phone data")
	}
	if err := os.WriteFile(filepath.Join(root, "data", "orders.txt"), []byte("beta"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := enterLogin(root, "010-1234-5678", same); err != nil {
		t.Fatal(err)
	}
	got, err = os.ReadFile(filepath.Join(root, "data", "products.txt"))
	if err != nil || string(got) != "alpha" {
		t.Fatalf("same phone lost data %q %v", got, err)
	}
	if _, err := os.Stat(filepath.Join(root, "data", "orders.txt")); !os.IsNotExist(err) {
		t.Fatal("first phone saw the second phone data")
	}
	if err := logoutLogin(root); err != nil {
		t.Fatal(err)
	}
	if activePhone(root) != "" {
		t.Fatal("still active")
	}
	if _, err := os.Stat(filepath.Join(root, "data", "products.txt")); !os.IsNotExist(err) {
		t.Fatal("logged out data still open")
	}
}

func TestAccountHTTP(t *testing.T) {
	root := t.TempDir()
	server := httptest.NewServer(accountHandler(root))
	defer server.Close()
	response, err := http.Post(server.URL+"/api/seller-login", "application/json", strings.NewReader(`{"phone":"01012345678"}`))
	if err != nil {
		t.Fatal(err)
	}
	defer response.Body.Close()
	if response.StatusCode != 200 {
		t.Fatal(response.Status)
	}
	bad, err := http.Post(server.URL+"/api/seller-enter", "application/json", strings.NewReader(`{"phone":"01012345678","password":"NOPE"}`))
	if err != nil {
		t.Fatal(err)
	}
	defer bad.Body.Close()
	if bad.StatusCode != http.StatusUnauthorized {
		t.Fatal(bad.Status)
	}
}

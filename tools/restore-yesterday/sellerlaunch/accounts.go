package main

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
)

var (
	errBadPhone    = errors.New("본인 전화번호를 입력해 주세요.")
	errBadPassword = errors.New("비밀번호가 맞지 않습니다.")
)

var phonePattern = regexp.MustCompile(`^01[016789]\d{7,8}$`)

var (
	accountMu    sync.Mutex
	stopProgram  = func(string) error { return nil }
	startProgram = func(string) error { return nil }
)

type accountRecord struct {
	Salt string `json:"salt"`
	Hash string `json:"hash"`
}

func normalizePhone(value string) (string, error) {
	digits := strings.Map(func(r rune) rune {
		if r >= '0' && r <= '9' {
			return r
		}
		return -1
	}, value)
	if strings.HasPrefix(digits, "82") && len(digits) >= 11 {
		digits = "0" + digits[2:]
	}
	if !phonePattern.MatchString(digits) {
		return "", errBadPhone
	}
	return digits, nil
}

func normalizePassword(value string) string {
	return strings.ToUpper(strings.Map(func(r rune) rune {
		if r == ' ' || r == '-' {
			return -1
		}
		return r
	}, strings.TrimSpace(value)))
}

func accountsPath(root string) string {
	return filepath.Join(root, "seller-accounts", "accounts.json")
}

func activePath(root string) string {
	return filepath.Join(root, "seller-accounts", "active.txt")
}

func pendingPath(root, phone string) string {
	return filepath.Join(root, "seller-accounts", "pending", phone+".txt")
}

func peopleData(root, phone string) string {
	return filepath.Join(root, "seller-accounts", "people", phone, "data")
}

func lockedData(root string) string {
	return filepath.Join(root, "seller-accounts", "locked")
}

func isLink(path string) bool {
	info, err := os.Lstat(path)
	if err != nil {
		return false
	}
	return info.Mode()&os.ModeSymlink != 0
}

func inspectData(path string) (real bool, hasFiles bool) {
	info, err := os.Lstat(path)
	if err != nil || isLink(path) || !info.IsDir() {
		return false, false
	}
	entries, err := os.ReadDir(path)
	if err != nil {
		return true, false
	}
	return true, len(entries) > 0
}

func loadAccounts(root string) (map[string]accountRecord, error) {
	data, err := os.ReadFile(accountsPath(root))
	if err != nil {
		if os.IsNotExist(err) {
			return map[string]accountRecord{}, nil
		}
		return nil, err
	}
	records := map[string]accountRecord{}
	if len(strings.TrimSpace(string(data))) == 0 {
		return records, nil
	}
	if err := json.Unmarshal(data, &records); err != nil {
		return nil, err
	}
	return records, nil
}

func saveAccounts(root string, records map[string]accountRecord) error {
	if err := os.MkdirAll(filepath.Dir(accountsPath(root)), 0o755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(records, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(accountsPath(root), append(data, '\n'), 0o600)
}

func generatePassword() string {
	const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
	raw := make([]byte, 8)
	if _, err := rand.Read(raw); err != nil {
		return "MODU2846"
	}
	for i := range raw {
		raw[i] = alphabet[int(raw[i])%len(alphabet)]
	}
	return string(raw)
}

func hashPassword(salt, password string) string {
	sum := sha256.Sum256([]byte(salt + "\n" + normalizePassword(password)))
	return hex.EncodeToString(sum[:])
}

func passwordMatches(record accountRecord, password string) bool {
	got := hashPassword(record.Salt, password)
	if len(got) != len(record.Hash) {
		return false
	}
	diff := 0
	for i := range got {
		diff |= int(got[i] ^ record.Hash[i])
	}
	return diff == 0 && normalizePassword(password) != ""
}

func readPending(root, phone string) string {
	data, err := os.ReadFile(pendingPath(root, phone))
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(data))
}

func issueLogin(root, rawPhone string) (string, string, error) {
	phone, err := normalizePhone(rawPhone)
	if err != nil {
		return "", "", err
	}
	accountMu.Lock()
	defer accountMu.Unlock()
	records, err := loadAccounts(root)
	if err != nil {
		return "", "", err
	}
	if _, ok := records[phone]; ok {
		if pending := readPending(root, phone); pending != "" {
			return "new", pending, nil
		}
		return "exists", "", nil
	}
	saltRaw := make([]byte, 16)
	if _, err := rand.Read(saltRaw); err != nil {
		return "", "", err
	}
	password := generatePassword()
	salt := hex.EncodeToString(saltRaw)
	records[phone] = accountRecord{Salt: salt, Hash: hashPassword(salt, password)}
	if err := saveAccounts(root, records); err != nil {
		return "", "", err
	}
	if err := os.MkdirAll(filepath.Dir(pendingPath(root, phone)), 0o755); err != nil {
		return "", "", err
	}
	if err := os.WriteFile(pendingPath(root, phone), []byte(password), 0o600); err != nil {
		return "", "", err
	}
	return "new", password, nil
}

func openPhone(root, phone string) error {
	home := peopleData(root, phone)
	live := filepath.Join(root, "data")
	if _, err := os.Stat(home); os.IsNotExist(err) {
		real, files := inspectData(live)
		if real && files {
			if err := os.MkdirAll(filepath.Dir(home), 0o755); err != nil {
				return err
			}
			if err := os.Rename(live, home); err != nil {
				return err
			}
		} else {
			if isLink(live) || real {
				if err := os.Remove(live); err != nil {
					return err
				}
			}
			if err := os.MkdirAll(home, 0o755); err != nil {
				return err
			}
		}
	} else if err != nil {
		return err
	}
	if err := relink(live, home); err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(activePath(root)), 0o755); err != nil {
		return err
	}
	return os.WriteFile(activePath(root), []byte(phone), 0o644)
}

func parkData(root string) error {
	live := filepath.Join(root, "data")
	_ = os.Remove(activePath(root))
	if !isLink(live) {
		return nil
	}
	return relink(live, lockedData(root))
}

func activePhone(root string) string {
	data, err := os.ReadFile(activePath(root))
	if err != nil {
		return ""
	}
	phone := strings.TrimSpace(string(data))
	if _, err := normalizePhone(phone); err != nil {
		return ""
	}
	return phone
}

func enterLogin(root, rawPhone, password string) error {
	phone, err := normalizePhone(rawPhone)
	if err != nil {
		return err
	}
	accountMu.Lock()
	defer accountMu.Unlock()
	records, err := loadAccounts(root)
	if err != nil {
		return err
	}
	record, ok := records[phone]
	if !ok || !passwordMatches(record, password) {
		return errBadPassword
	}
	if err := stopProgram(root); err != nil {
		return err
	}
	if err := openPhone(root, phone); err != nil {
		return err
	}
	_ = os.Remove(pendingPath(root, phone))
	return startProgram(root)
}

func logoutLogin(root string) error {
	if err := stopProgram(root); err != nil {
		return err
	}
	if err := parkData(root); err != nil {
		return err
	}
	return startProgram(root)
}

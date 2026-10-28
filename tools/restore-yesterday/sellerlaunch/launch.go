package main

import (
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

const sellerListenPort = "8788"

var (
	errMissingProgram = errors.New("셀러용 프로그램을 찾지 못했습니다.")
	errMasterLauncher = errors.New("셀러용 프로그램 파일이 바뀌었습니다. 모두모두AI-셀러용-설치.exe 를 다시 실행해 주세요.")
)

func ensureSellerEdition(dir string) error {
	return os.WriteFile(filepath.Join(dir, "edition.txt"), []byte("test\r\n"), 0o644)
}

func removeMasterLaunchers(dir string) error {
	for _, name := range []string{"어제오후9시.vbs", "idle-update.vbs"} {
		path := filepath.Join(dir, name)
		if err := os.Remove(path); err != nil && !os.IsNotExist(err) {
			return err
		}
	}
	return nil
}

func sellerEnviron() []string {
	out := make([]string, 0, len(os.Environ())+2)
	for _, item := range os.Environ() {
		if strings.HasPrefix(item, "UPLOADER_PORT=") || strings.HasPrefix(item, "UPLOADER_SKIP_UPDATE=") {
			continue
		}
		out = append(out, item)
	}
	return append(out, "UPLOADER_PORT="+sellerListenPort, "UPLOADER_SKIP_UPDATE=1")
}

func sellerCommand(target, dir string) *exec.Cmd {
	cmd := exec.Command(target)
	cmd.Dir = dir
	cmd.Env = sellerEnviron()
	return cmd
}

func prepareSellerCommand(dir string) (*exec.Cmd, error) {
	target := filepath.Join(dir, "MODUMODU.exe")
	info, err := os.Stat(target)
	if err != nil || info.IsDir() {
		return nil, errMissingProgram
	}
	if !keepProgramExe(target) {
		return nil, errMasterLauncher
	}
	if err := ensureSellerEdition(dir); err != nil {
		return nil, err
	}
	if err := removeMasterLaunchers(dir); err != nil {
		return nil, err
	}
	return sellerCommand(target, dir), nil
}

func startModumodu(dir string) error {
	cmd, err := prepareSellerCommand(dir)
	if err != nil {
		return err
	}
	return cmd.Start()
}

package main

import (
	"path/filepath"
	"sort"
)

// oldestBackup returns the earliest same-day backup created before today's
// screen edits. Names look like app.js.bak-20261027-164205.
func oldestBackup(dir, name string) (string, bool) {
	matches, err := filepath.Glob(filepath.Join(dir, name+".bak-20261027*"))
	if err != nil || len(matches) == 0 {
		return "", false
	}
	sort.Strings(matches)
	return matches[0], true
}

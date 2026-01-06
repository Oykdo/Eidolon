package psnx

import (
	"encoding/hex"
)

// bytesToHex converts bytes to hex string
func bytesToHex(b []byte) string {
	return hex.EncodeToString(b)
}

// hexToBytes converts hex string to bytes
func hexToBytes(s string) []byte {
	if len(s) >= 2 && s[:2] == "0x" {
		s = s[2:]
	}
	b, _ := hex.DecodeString(s)
	return b
}

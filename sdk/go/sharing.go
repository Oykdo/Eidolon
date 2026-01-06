package psnx

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/binary"
	"errors"
	"math/big"
)

// Prime for GF(p) - 2^256 - 189
var prime *big.Int

func init() {
	prime = new(big.Int).Exp(big.NewInt(2), big.NewInt(256), nil)
	prime.Sub(prime, big.NewInt(189))
}

// Share represents a Shamir secret share
type Share struct {
	Index     int    `json:"index"`
	Data      []byte `json:"data"`
	Threshold int    `json:"threshold"`
	Total     int    `json:"total"`
	Checksum  string `json:"checksum"`
}

// SecretSharing implements Shamir's Secret Sharing
type SecretSharing struct {
	threshold int
	total     int
}

// NewSecretSharing creates a new secret sharing instance
func NewSecretSharing(threshold, total int) (*SecretSharing, error) {
	if threshold < 2 {
		return nil, errors.New("threshold must be >= 2")
	}
	if total < threshold {
		return nil, errors.New("total must be >= threshold")
	}
	if total > 255 {
		return nil, errors.New("maximum 255 shares")
	}

	return &SecretSharing{
		threshold: threshold,
		total:     total,
	}, nil
}

// Split divides a secret into N shares
func (ss *SecretSharing) Split(secret []byte) ([]*Share, error) {
	if len(secret) > 32 {
		return nil, errors.New("secret too large (max 32 bytes)")
	}

	// Convert secret to big int
	secretInt := new(big.Int).SetBytes(secret)

	// Generate polynomial coefficients
	coefficients := make([]*big.Int, ss.threshold)
	coefficients[0] = secretInt

	for i := 1; i < ss.threshold; i++ {
		randBytes := make([]byte, 32)
		if _, err := rand.Read(randBytes); err != nil {
			return nil, err
		}
		coeff := new(big.Int).SetBytes(randBytes)
		coeff.Mod(coeff, new(big.Int).Sub(prime, big.NewInt(1)))
		coeff.Add(coeff, big.NewInt(1))
		coefficients[i] = coeff
	}

	// Evaluate polynomial at N points
	shares := make([]*Share, ss.total)
	for x := 1; x <= ss.total; x++ {
		y := ss.evaluate(coefficients, big.NewInt(int64(x)))

		// Convert to 32 bytes
		yBytes := make([]byte, 32)
		yBytesRaw := y.Bytes()
		copy(yBytes[32-len(yBytesRaw):], yBytesRaw)

		// Calculate checksum
		indexBytes := make([]byte, 4)
		binary.BigEndian.PutUint32(indexBytes, uint32(x))
		toHash := append(yBytes, indexBytes...)
		hash := sha256.Sum256(toHash)
		checksum := bytesToHex(hash[:4])

		shares[x-1] = &Share{
			Index:     x,
			Data:      yBytes,
			Threshold: ss.threshold,
			Total:     ss.total,
			Checksum:  checksum,
		}
	}

	return shares, nil
}

// Reconstruct recovers the secret from K shares
func (ss *SecretSharing) Reconstruct(shares []*Share) ([]byte, error) {
	if len(shares) < ss.threshold {
		return nil, errors.New("not enough shares")
	}

	// Verify checksums
	for _, share := range shares {
		if !ss.VerifyShare(share) {
			return nil, errors.New("share corrupted: " + string(rune(share.Index)))
		}
	}

	// Use first K shares
	useShares := shares[:ss.threshold]

	// Check for duplicates
	seen := make(map[int]bool)
	for _, s := range useShares {
		if seen[s.Index] {
			return nil, errors.New("duplicate shares")
		}
		seen[s.Index] = true
	}

	// Convert to points
	points := make([][2]*big.Int, len(useShares))
	for i, s := range useShares {
		points[i] = [2]*big.Int{
			big.NewInt(int64(s.Index)),
			new(big.Int).SetBytes(s.Data),
		}
	}

	// Lagrange interpolation at x=0
	secretInt := ss.lagrange(points, big.NewInt(0))

	// Convert back to bytes
	secretBytes := secretInt.Bytes()

	return secretBytes, nil
}

func (ss *SecretSharing) evaluate(coefficients []*big.Int, x *big.Int) *big.Int {
	result := big.NewInt(0)
	xPower := big.NewInt(1)

	for _, coeff := range coefficients {
		term := new(big.Int).Mul(coeff, xPower)
		result.Add(result, term)
		result.Mod(result, prime)
		xPower.Mul(xPower, x)
		xPower.Mod(xPower, prime)
	}

	return result
}

func (ss *SecretSharing) lagrange(points [][2]*big.Int, x *big.Int) *big.Int {
	result := big.NewInt(0)

	for i, point := range points {
		xi, yi := point[0], point[1]

		num := big.NewInt(1)
		den := big.NewInt(1)

		for j, other := range points {
			if i != j {
				xj := other[0]

				// num *= (x - xj)
				diff := new(big.Int).Sub(x, xj)
				num.Mul(num, diff)
				num.Mod(num, prime)

				// den *= (xi - xj)
				diff = new(big.Int).Sub(xi, xj)
				den.Mul(den, diff)
				den.Mod(den, prime)
			}
		}

		// Modular inverse of den
		denInv := new(big.Int).ModInverse(den, prime)
		if denInv == nil {
			continue
		}

		// coeff = num * denInv
		coeff := new(big.Int).Mul(num, denInv)
		coeff.Mod(coeff, prime)

		// result += yi * coeff
		term := new(big.Int).Mul(yi, coeff)
		result.Add(result, term)
		result.Mod(result, prime)
	}

	// Handle negative result
	if result.Sign() < 0 {
		result.Add(result, prime)
	}

	return result
}

// VerifyShare checks the checksum of a share
func (ss *SecretSharing) VerifyShare(share *Share) bool {
	indexBytes := make([]byte, 4)
	binary.BigEndian.PutUint32(indexBytes, uint32(share.Index))
	toHash := append(share.Data, indexBytes...)
	hash := sha256.Sum256(toHash)
	expected := bytesToHex(hash[:4])
	return share.Checksum == expected
}

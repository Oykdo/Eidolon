package psnx

import (
	"crypto/rand"
	"crypto/sha256"
	"fmt"
	"math/big"
	"time"
)

// Schnorr group parameters (RFC 5114 - 2048-bit MODP Group)
var (
	P *big.Int
	Q *big.Int
	G *big.Int
)

func init() {
	// Initialize Schnorr parameters
	P, _ = new(big.Int).SetString(
		"FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"+
			"29024E088A67CC74020BBEA63B139B22514A08798E3404DD"+
			"EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"+
			"E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"+
			"EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"+
			"C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"+
			"83655D23DCA3AD961C62F356208552BB9ED529077096966D"+
			"670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"+
			"E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9"+
			"DE2BCBF6955817183995497CEA956AE515D2261898FA0510"+
			"15728E5A8AACAA68FFFFFFFFFFFFFFFF", 16)
	
	Q = new(big.Int).Sub(P, big.NewInt(1))
	Q.Div(Q, big.NewInt(2))
	
	G = big.NewInt(2)
}

// ZKPProof represents a Zero-Knowledge Proof
type ZKPProof struct {
	Commitment string  `json:"commitment"`
	Challenge  string  `json:"challenge"`
	Response   string  `json:"response"`
	PublicKey  string  `json:"publicKey"`
	Message    string  `json:"message"`
	Timestamp  float64 `json:"timestamp"`
}

// ZKPProver creates Zero-Knowledge Proofs
type ZKPProver struct {
	x *big.Int // Private key
	Y *big.Int // Public key
}

// NewZKPProver creates a new prover from a vault key
func NewZKPProver(vaultKey []byte) (*ZKPProver, error) {
	if len(vaultKey) != 32 {
		return nil, fmt.Errorf("vault key must be 32 bytes")
	}

	// Derive private key
	combined := append([]byte("PSNX_ZKP_PRIVATE_"), vaultKey...)
	hash := sha256.Sum256(combined)

	x := new(big.Int).SetBytes(hash[:])
	x.Mod(x, Q)
	if x.Sign() == 0 {
		x.SetInt64(1)
	}

	Y := new(big.Int).Exp(G, x, P)

	return &ZKPProver{x: x, Y: Y}, nil
}

// GetPublicKey returns the public key
func (p *ZKPProver) GetPublicKey() *big.Int {
	return new(big.Int).Set(p.Y)
}

// GetPublicKeyHex returns the public key as hex string
func (p *ZKPProver) GetPublicKeyHex() string {
	return "0x" + p.Y.Text(16)
}

// GetFingerprint returns the key fingerprint
func (p *ZKPProver) GetFingerprint() string {
	yBytes := p.Y.Bytes()
	hash := sha256.Sum256(yBytes)
	return bytesToHex(hash[:8])
}

// CreateProof creates a ZKP proof for a challenge
func (p *ZKPProver) CreateProof(challenge string) (*ZKPProofResult, error) {
	message := []byte(challenge)
	timestamp := float64(time.Now().UnixMilli()) / 1000.0

	// Generate random k
	kBytes := make([]byte, 32)
	if _, err := rand.Read(kBytes); err != nil {
		return nil, err
	}
	k := new(big.Int).SetBytes(kBytes)
	k.Mod(k, new(big.Int).Sub(Q, big.NewInt(1)))
	k.Add(k, big.NewInt(1))

	// Commitment: R = g^k mod p
	R := new(big.Int).Exp(G, k, P)

	// Challenge: c = H(R || Y || m)
	hasher := sha256.New()
	hasher.Write(R.Bytes())
	hasher.Write(p.Y.Bytes())
	hasher.Write(message)
	cHash := hasher.Sum(nil)

	c := new(big.Int).SetBytes(cHash)
	c.Mod(c, Q)

	// Response: s = k + c*x mod Q
	s := new(big.Int).Mul(c, p.x)
	s.Add(s, k)
	s.Mod(s, Q)

	proof := &ZKPProof{
		Commitment: "0x" + R.Text(16),
		Challenge:  "0x" + c.Text(16),
		Response:   "0x" + s.Text(16),
		PublicKey:  "0x" + p.Y.Text(16),
		Message:    bytesToHex(message),
		Timestamp:  timestamp,
	}

	return &ZKPProofResult{
		Proof:          proof,
		Challenge:      challenge,
		KeyFingerprint: p.GetFingerprint(),
		Timestamp:      timestamp,
	}, nil
}

// ZKPProofResult contains the proof and metadata
type ZKPProofResult struct {
	Proof          *ZKPProof `json:"proof"`
	Challenge      string    `json:"challenge"`
	KeyFingerprint string    `json:"keyFingerprint"`
	Timestamp      float64   `json:"timestamp"`
}

// ZKPVerifier verifies Zero-Knowledge Proofs
type ZKPVerifier struct{}

// NewZKPVerifier creates a new verifier
func NewZKPVerifier() *ZKPVerifier {
	return &ZKPVerifier{}
}

// Verify verifies a ZKP proof
func (v *ZKPVerifier) Verify(authData *ZKPProofResult, expectedChallenge string, maxAgeSeconds float64) (bool, string) {
	proof := authData.Proof

	// Verify challenge
	if authData.Challenge != expectedChallenge {
		return false, "Challenge mismatch"
	}

	// Verify age
	age := float64(time.Now().UnixMilli())/1000.0 - proof.Timestamp
	if age > maxAgeSeconds {
		return false, fmt.Sprintf("Proof expired (age: %.1fs)", age)
	}
	if age < -60 {
		return false, "Proof from future"
	}

	// Parse values
	R, ok := new(big.Int).SetString(proof.Commitment[2:], 16)
	if !ok {
		return false, "Invalid commitment"
	}
	c, ok := new(big.Int).SetString(proof.Challenge[2:], 16)
	if !ok {
		return false, "Invalid challenge"
	}
	s, ok := new(big.Int).SetString(proof.Response[2:], 16)
	if !ok {
		return false, "Invalid response"
	}
	Y, ok := new(big.Int).SetString(proof.PublicKey[2:], 16)
	if !ok {
		return false, "Invalid public key"
	}
	message := hexToBytes(proof.Message)

	// Verify challenge hash
	hasher := sha256.New()
	hasher.Write(R.Bytes())
	hasher.Write(Y.Bytes())
	hasher.Write(message)
	expectedCHash := hasher.Sum(nil)
	expectedC := new(big.Int).SetBytes(expectedCHash)
	expectedC.Mod(expectedC, Q)

	if expectedC.Cmp(c) != 0 {
		return false, "Invalid challenge hash"
	}

	// Verify: g^s == R * Y^c mod p
	lhs := new(big.Int).Exp(G, s, P)

	yc := new(big.Int).Exp(Y, c, P)
	rhs := new(big.Int).Mul(R, yc)
	rhs.Mod(rhs, P)

	if lhs.Cmp(rhs) != 0 {
		return false, "Cryptographic verification failed"
	}

	return true, "OK"
}

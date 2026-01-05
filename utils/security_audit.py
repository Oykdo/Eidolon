"""
Security Audit Module for Quantum Cryptographic System

This module provides comprehensive security auditing capabilities for the
Poly-Spinor Nexus quantum cryptographic system, including entropy analysis,
cryptographic strength evaluation, and compliance checks.
"""

import numpy as np
import hashlib
import math
from typing import Dict, List, Tuple, Optional, Union
from collections import Counter
import scipy.stats as stats

# ============================================================================
# Entropy Analysis
# ============================================================================

class EntropyAnalyzer:
    """
    Analyzes entropy in cryptographic keys and quantum states.
    """

    @staticmethod
    def shannon_entropy(data: bytes) -> float:
        """
        Calculate Shannon entropy of byte data.

        :param data: Byte sequence
        :return: Entropy in bits per byte
        """
        if not data:
            return 0.0

        byte_counts = Counter(data)
        entropy = 0.0
        data_len = len(data)

        for count in byte_counts.values():
            probability = count / data_len
            entropy -= probability * math.log2(probability)

        return entropy

    @staticmethod
    def min_entropy(data: bytes) -> float:
        """
        Calculate min-entropy of byte data.

        :param data: Byte sequence
        :return: Min-entropy in bits
        """
        if not data:
            return 0.0

        byte_counts = Counter(data)
        max_freq = max(byte_counts.values())
        probability = max_freq / len(data)
        return -math.log2(probability)

    @staticmethod
    def quantum_state_entropy(rho: np.ndarray) -> float:
        """
        Calculate von Neumann entropy of quantum density matrix.

        :param rho: Density matrix
        :return: Entropy in bits
        """
        eigenvals = np.linalg.eigvals(rho)
        eigenvals = eigenvals[eigenvals > 1e-12]  # Remove numerical zeros
        entropy = -np.sum(eigenvals * np.log2(eigenvals))
        return np.real(entropy)

    @staticmethod
    def test_randomness(data: bytes, num_tests: int = 5) -> Dict[str, float]:
        """
        Perform basic randomness tests on data.

        :param data: Byte sequence to test
        :param num_tests: Number of tests to perform
        :return: Dictionary of test results (p-values)
        """
        results = {}

        # Frequency test (monobit)
        bit_string = ''.join(format(byte, '08b') for byte in data)
        ones = bit_string.count('1')
        zeros = bit_string.count('0')
        expected = (ones + zeros) / 2
        chi_square = ((ones - expected)**2 + (zeros - expected)**2) / expected
        results['frequency_test'] = 1 - stats.chi2.cdf(chi_square, 1)

        # Runs test
        runs = 1
        for i in range(1, len(bit_string)):
            if bit_string[i] != bit_string[i-1]:
                runs += 1
        expected_runs = (2 * ones * zeros) / (ones + zeros) + 1
        variance_runs = (2 * ones * zeros * (2 * ones * zeros - ones - zeros)) / ((ones + zeros)**2 * (ones + zeros - 1))
        if variance_runs > 0:
            z = (runs - expected_runs) / math.sqrt(variance_runs)
            results['runs_test'] = 2 * (1 - stats.norm.cdf(abs(z)))
        else:
            results['runs_test'] = 0.0

        # Additional tests can be added
        results['entropy_ratio'] = EntropyAnalyzer.shannon_entropy(data) / 8.0  # Max 8 bits/byte

        return results

# ============================================================================
# Cryptographic Strength Evaluation
# ============================================================================

class StrengthEvaluator:
    """
    Evaluates cryptographic strength against classical and quantum attacks.
    """

    QUANTUM_THREATS = {
        'rsa': {'classical': 1024, 'quantum': 2048},  # Shor's algorithm
        'ecc': {'classical': 256, 'quantum': 512},   # Grover's algorithm
        'aes': {'classical': 128, 'quantum': 256},   # Grover's algorithm
        'hash': {'classical': 256, 'quantum': 512}   # Grover's algorithm
    }

    @staticmethod
    def evaluate_key_strength(key_size: int, algorithm: str, threat_model: str = 'quantum') -> Dict[str, Union[str, int]]:
        """
        Evaluate key strength against specified threat model.

        :param key_size: Key size in bits
        :param algorithm: Algorithm type ('rsa', 'ecc', 'aes', 'hash')
        :param threat_model: 'classical' or 'quantum'
        :return: Evaluation results
        """
        if algorithm not in StrengthEvaluator.QUANTUM_THREATS:
            return {'status': 'unknown', 'recommended': 'N/A', 'secure': False}

        thresholds = StrengthEvaluator.QUANTUM_THREATS[algorithm]
        recommended = thresholds.get(threat_model, thresholds['quantum'])

        secure = key_size >= recommended
        status = 'secure' if secure else 'vulnerable'

        return {
            'status': status,
            'recommended': recommended,
            'current': key_size,
            'secure': secure
        }

    @staticmethod
    def analyze_algorithm_vulnerabilities(algorithm: str) -> Dict[str, str]:
        """
        Analyze known vulnerabilities for an algorithm.

        :param algorithm: Algorithm name
        :return: Vulnerability analysis
        """
        vulnerabilities = {
            'rsa': 'Vulnerable to Shor\'s algorithm on quantum computers',
            'ecc': 'Vulnerable to Grover\'s algorithm, requires larger keys',
            'aes': 'Vulnerable to Grover\'s algorithm, requires larger keys',
            'sha256': 'Vulnerable to collision attacks with Grover\'s algorithm',
            'bb84': 'Secure against eavesdropping if properly implemented',
            'ek91': 'Secure against eavesdropping with quantum no-cloning'
        }

        return {
            'algorithm': algorithm,
            'vulnerabilities': vulnerabilities.get(algorithm, 'Unknown'),
            'quantum_resistant': algorithm in ['bb84', 'ek91']
        }

    @staticmethod
    def assess_post_quantum_readiness(system_config: Dict) -> Dict[str, Union[str, bool]]:
        """
        Assess system readiness for post-quantum cryptography.

        :param system_config: System configuration dictionary
        :return: Assessment results
        """
        assessment = {
            'overall_readiness': 'unknown',
            'recommendations': [],
            'critical_issues': []
        }

        # Check key sizes
        if 'key_sizes' in system_config:
            for algo, size in system_config['key_sizes'].items():
                eval_result = StrengthEvaluator.evaluate_key_strength(size, algo)
                if not eval_result['secure']:
                    assessment['critical_issues'].append(f"{algo.upper()} key size {size} too small")
                    assessment['recommendations'].append(f"Upgrade {algo.upper()} to {eval_result['recommended']} bits")

        # Check algorithms
        if 'algorithms' in system_config:
            for algo in system_config['algorithms']:
                vuln = StrengthEvaluator.analyze_algorithm_vulnerabilities(algo)
                if not vuln['quantum_resistant']:
                    assessment['recommendations'].append(f"Consider migrating from {algo.upper()} to post-quantum alternative")

        assessment['overall_readiness'] = 'ready' if not assessment['critical_issues'] else 'needs_upgrade'

        return assessment

# ============================================================================
# Compliance Checks
# ============================================================================

class ComplianceChecker:
    """
    Checks compliance with cryptographic standards and regulations.
    """

    NIST_STANDARDS = {
        'post_quantum': {
            'min_key_size': {'rsa': 3072, 'ecc': 384, 'aes': 256},
            'approved_algorithms': ['aes-256', 'sha-256', 'sha-384', 'ecdsa-p384']
        },
        'quantum_key_distribution': {
            'protocols': ['bb84', 'ek91', 'decoy_state'],
            'error_rates': {'max': 0.11}  # For BB84
        }
    }

    @staticmethod
    def check_nist_compliance(system_config: Dict) -> Dict[str, Union[str, List[str]]]:
        """
        Check compliance with NIST standards.

        :param system_config: System configuration
        :return: Compliance report
        """
        report = {
            'compliant': True,
            'violations': [],
            'recommendations': []
        }

        # Check key sizes
        if 'key_sizes' in system_config:
            nist_min = ComplianceChecker.NIST_STANDARDS['post_quantum']['min_key_size']
            for algo, size in system_config['key_sizes'].items():
                if algo in nist_min and size < nist_min[algo]:
                    report['compliant'] = False
                    report['violations'].append(f"{algo.upper()} key size {size} < NIST minimum {nist_min[algo]}")

        # Check algorithms
        if 'algorithms' in system_config:
            approved = ComplianceChecker.NIST_STANDARDS['post_quantum']['approved_algorithms']
            for algo in system_config['algorithms']:
                if algo not in approved:
                    report['recommendations'].append(f"Consider NIST-approved alternative for {algo}")

        return report

    @staticmethod
    def check_quantum_protocol_compliance(protocol: str, parameters: Dict) -> Dict[str, Union[str, bool]]:
        """
        Check compliance of quantum key distribution protocol.

        :param protocol: Protocol name
        :param parameters: Protocol parameters
        :return: Compliance check
        """
        check = {
            'protocol': protocol,
            'compliant': True,
            'issues': []
        }

        if protocol.lower() == 'bb84':
            if 'error_rate' in parameters:
                max_error = ComplianceChecker.NIST_STANDARDS['quantum_key_distribution']['error_rates']['max']
                if parameters['error_rate'] > max_error:
                    check['compliant'] = False
                    check['issues'].append(f"Error rate {parameters['error_rate']:.3f} > max {max_error}")

        elif protocol.lower() not in ComplianceChecker.NIST_STANDARDS['quantum_key_distribution']['protocols']:
            check['compliant'] = False
            check['issues'].append(f"Protocol {protocol} not in approved list")

        return check

# ============================================================================
# Quantum Security Auditor
# ============================================================================

class QuantumSecurityAuditor:
    """
    Audits quantum-specific security aspects.
    """

    @staticmethod
    def verify_entanglement(state: np.ndarray, dimension: int = 7) -> Dict[str, Union[float, bool]]:
        """
        Verify if a quantum state shows entanglement signatures.

        :param state: Quantum state vector
        :return: Verification results
        """
        verification = {
            'is_entangled': False,
            'purity': 0.0,
            'concurrence': 0.0,
            'negativity': 0.0
        }

        # For two qudits, check if separable
        if len(state) == dimension ** 2:
            # Reshape to matrix for Schmidt decomposition
            state_matrix = state.reshape((dimension, dimension))

            # Compute singular values
            singular_vals = np.linalg.svd(state_matrix, compute_uv=False)

            # Check if rank > 1 (entangled)
            rank = np.sum(singular_vals > 1e-10)
            verification['is_entangled'] = rank > 1

            # Concurrence approximation
            if len(singular_vals) >= 2:
                verification['concurrence'] = np.sqrt(2 * (1 - np.sum(singular_vals**2)))

        # Purity
        rho = np.outer(state, np.conj(state))
        verification['purity'] = np.real(np.trace(rho @ rho))

        return verification

    @staticmethod
    def audit_bell_violation(correlations: np.ndarray) -> Dict[str, Union[float, bool]]:
        """
        Audit Bell inequality violations.

        :param correlations: Correlation tensor
        :return: Audit results
        """
        audit = {
            'violates_bell': False,
            'chsh_value': 0.0,
            'confidence': 0.0
        }

        if correlations.shape == (2, 2):
            # CHSH inequality
            chsh = correlations[0,0] + correlations[0,1] + correlations[1,0] - correlations[1,1]
            audit['chsh_value'] = abs(chsh)
            audit['violates_bell'] = abs(chsh) > 2

            # Simple confidence based on violation strength
            if audit['violates_bell']:
                audit['confidence'] = min(1.0, (abs(chsh) - 2) / 2.0)

        return audit

    @staticmethod
    def assess_randomness_extraction(efficiency: float, input_entropy: float) -> Dict[str, Union[float, str]]:
        """
        Assess randomness extraction from quantum systems.

        :param efficiency: Extraction efficiency
        :param input_entropy: Input entropy
        :return: Assessment
        """
        assessment = {
            'extraction_rate': efficiency,
            'output_entropy': input_entropy * efficiency,
            'security_level': 'unknown'
        }

        if efficiency > 0.8:
            assessment['security_level'] = 'high'
        elif efficiency > 0.5:
            assessment['security_level'] = 'medium'
        else:
            assessment['security_level'] = 'low'

        return assessment

# ============================================================================
# Main Security Auditor
# ============================================================================

class SecurityAuditor:
    """
    Main security auditor for the quantum cryptographic system.
    """

    def __init__(self):
        self.entropy_analyzer = EntropyAnalyzer()
        self.strength_evaluator = StrengthEvaluator()
        self.compliance_checker = ComplianceChecker()
        self.quantum_auditor = QuantumSecurityAuditor()

    def audit_entropy(self, data: Union[bytes, np.ndarray]) -> Dict[str, float]:
        """
        Comprehensive entropy audit.

        :param data: Data to audit (bytes or quantum state)
        :return: Entropy metrics
        """
        if isinstance(data, bytes):
            return {
                'shannon_entropy': self.entropy_analyzer.shannon_entropy(data),
                'min_entropy': self.entropy_analyzer.min_entropy(data),
                'randomness_tests': self.entropy_analyzer.test_randomness(data)
            }
        elif isinstance(data, np.ndarray):
            return {
                'von_neumann_entropy': self.entropy_analyzer.quantum_state_entropy(
                    np.outer(data, np.conj(data)) if data.ndim == 1 else data
                )
            }
        else:
            raise ValueError("Unsupported data type for entropy audit")

    def audit_cryptographic_strength(self, system_config: Dict) -> Dict[str, Union[str, Dict]]:
        """
        Audit cryptographic strength.

        :param system_config: System configuration
        :return: Strength assessment
        """
        return self.strength_evaluator.assess_post_quantum_readiness(system_config)

    def audit_compliance(self, system_config: Dict) -> Dict[str, Union[str, List[str]]]:
        """
        Audit compliance with standards.

        :param system_config: System configuration
        :return: Compliance report
        """
        nist_compliance = self.compliance_checker.check_nist_compliance(system_config)

        # Add quantum protocol checks if present
        if 'quantum_protocols' in system_config:
            for protocol, params in system_config['quantum_protocols'].items():
                proto_check = self.compliance_checker.check_quantum_protocol_compliance(protocol, params)
                if not proto_check['compliant']:
                    nist_compliance['violations'].extend(proto_check['issues'])

        return nist_compliance

    def audit_quantum_security(self, quantum_state: Optional[np.ndarray] = None,
                             correlations: Optional[np.ndarray] = None) -> Dict[str, Dict]:
        """
        Audit quantum-specific security aspects.

        :param quantum_state: Quantum state to analyze
        :param correlations: Bell correlations
        :return: Quantum security audit
        """
        audit_results = {}

        if quantum_state is not None:
            audit_results['entanglement'] = self.quantum_auditor.verify_entanglement(quantum_state)

        if correlations is not None:
            audit_results['bell_violation'] = self.quantum_auditor.audit_bell_violation(correlations)

        return audit_results

    def comprehensive_audit(self, system_config: Dict, quantum_data: Optional[Dict] = None) -> Dict[str, Dict]:
        """
        Perform comprehensive security audit.

        :param system_config: System configuration
        :param quantum_data: Optional quantum data (state, correlations)
        :return: Complete audit report
        """
        report = {
            'cryptographic_strength': self.audit_cryptographic_strength(system_config),
            'compliance': self.audit_compliance(system_config),
            'quantum_security': {}
        }

        if quantum_data:
            report['quantum_security'] = self.audit_quantum_security(
                quantum_data.get('state'),
                quantum_data.get('correlations')
            )

        # Overall assessment
        critical_issues = []
        if not report['compliance']['compliant']:
            critical_issues.extend(report['compliance']['violations'])
        if report['cryptographic_strength']['overall_readiness'] == 'needs_upgrade':
            critical_issues.extend(report['cryptographic_strength']['critical_issues'])

        report['overall_assessment'] = {
            'status': 'secure' if not critical_issues else 'vulnerable',
            'critical_issues': critical_issues,
            'recommendations': report['cryptographic_strength'].get('recommendations', []) +
                             report['compliance'].get('recommendations', [])
        }

        return report

# ============================================================================
# Utility Functions
# ============================================================================

def audit_key_entropy(key: bytes) -> Dict[str, float]:
    """
    Convenience function to audit key entropy.

    :param key: Key bytes
    :return: Entropy metrics
    """
    auditor = SecurityAuditor()
    return auditor.audit_entropy(key)

def check_system_security(system_config: Dict) -> str:
    """
    Quick security check returning overall status.

    :param system_config: System configuration
    :return: Security status string
    """
    auditor = SecurityAuditor()
    audit = auditor.comprehensive_audit(system_config)
    return audit['overall_assessment']['status']

def verify_quantum_entanglement(state: np.ndarray) -> bool:
    """
    Quick check for quantum entanglement.

    :param state: Quantum state
    :return: True if entangled
    """
    auditor = SecurityAuditor()
    result = auditor.audit_quantum_security(quantum_state=state)
    return result.get('entanglement', {}).get('is_entangled', False)
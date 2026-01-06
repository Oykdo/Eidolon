/**
 * Exceptions pour le SDK
 */

export class PSNXError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'PSNXError';
  }
}

export class AuthenticationError extends PSNXError {
  constructor(message: string) {
    super(message);
    this.name = 'AuthenticationError';
  }
}

export class EncryptionError extends PSNXError {
  constructor(message: string) {
    super(message);
    this.name = 'EncryptionError';
  }
}

export class DecryptionError extends PSNXError {
  constructor(message: string) {
    super(message);
    this.name = 'DecryptionError';
  }
}

export class NetworkError extends PSNXError {
  statusCode: number;
  
  constructor(message: string, statusCode: number = 0) {
    super(message);
    this.name = 'NetworkError';
    this.statusCode = statusCode;
  }
}

export class ValidationError extends PSNXError {
  constructor(message: string) {
    super(message);
    this.name = 'ValidationError';
  }
}

export class ShareError extends PSNXError {
  constructor(message: string) {
    super(message);
    this.name = 'ShareError';
  }
}

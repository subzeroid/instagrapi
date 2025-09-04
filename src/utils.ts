import { randomUUID, createCipheriv, publicEncrypt, randomBytes, createHmac } from 'bun:crypto';

// This is a placeholder public key and key ID.
// In the real implementation, this would be fetched from Instagram's API.
const INSTAGRAM_PUBLIC_KEY_ID = '107';
const INSTAGRAM_PUBLIC_KEY = `-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxL2yV/scAg+ln+ceY9zD
yX1I+Pa1w2b+h7gq+sIit4e7mDce1+52ofM2gMvg2iAPe4j9/gZ2/cUD8Po5dprt
eLdM7Pihz2yN9lEx8S8aK3m19g/6Wq37jTKfSPlurF9iwyWwnt0Pgaf5a7GlAYYJ
cI0S2xDBMhBREA9/uWb9adIDnnO6pukJ2dMfqHwXl7JjWRn1vOTo8pGk8Yv8s/gU
vDk3E/2pGzUfR8z/yqUu9ZvSygzLGyI0f+B4xctgreHl2h4Yy3/pT2xYjGjxAlJG
RqcYpDECMt/2ixfDRz1Pyj1E5EV7n8a2xtIBSWjYMXV+a4eYl9YnRPTwMboYsvDR
JQIDAQAB
-----END PUBLIC KEY-----`;

export function generateUuid(): string {
  return randomUUID();
}

export function generateJazoest(phoneId: string): string {
    const timestamp = Math.floor(Date.now() / 1000);
    const jazoest = `2${timestamp}`;
    const hmac = createHmac('sha256', 'DEFAULT_KEY'); // Note: The key is not available in the source
    hmac.update(phoneId);
    const hashed = hmac.digest('hex');
    // The python implementation seems to have a different logic, this is a placeholder
    return jazoest;
}


export function passwordEncrypt(password: string): string {
  const time = Math.floor(Date.now() / 1000).toString();
  const key = randomBytes(32);
  const iv = randomBytes(12);

  // 1. RSA encrypt the session key
  const rsaEncrypted = publicEncrypt(
    {
      key: INSTAGRAM_PUBLIC_KEY,
      padding: 1, // crypto.constants.RSA_PKCS1_PADDING
    },
    key
  );

  // 2. AES-GCM encrypt the password
  const cipher = createCipheriv('aes-256-gcm', key, iv);
  cipher.setAAD(Buffer.from(time)); // Associated data is the timestamp
  const encryptedPassword = Buffer.concat([cipher.update(Buffer.from(password)), cipher.final()]);
  const tag = cipher.getAuthTag();

  // 3. Construct the final payload
  const publicKeyIdBuf = Buffer.alloc(1);
  publicKeyIdBuf.writeUInt8(parseInt(INSTAGRAM_PUBLIC_KEY_ID, 10), 0);

  const rsaEncryptedLenBuf = Buffer.alloc(2);
  rsaEncryptedLenBuf.writeUInt16LE(rsaEncrypted.length, 0);

  const payload = Buffer.concat([
    Buffer.from([1]), // Version
    publicKeyIdBuf,
    iv,
    rsaEncryptedLenBuf,
    rsaEncrypted,
    tag,
    encryptedPassword,
  ]);

  return `#PWD_INSTAGRAM:4:${time}:${payload.toString('base64')}`;
}

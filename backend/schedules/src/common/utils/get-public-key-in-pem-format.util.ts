export function getPublicKeyInPemFormat(publicKey: string): Buffer {
  return Buffer.from(
    `-----BEGIN PUBLIC KEY-----\n${publicKey}\n-----END PUBLIC KEY-----`,
  );
}

import jwt
from fastapi import HTTPException, status, Header, Request
from jwt import PyJWTError, ExpiredSignatureError, InvalidTokenError, PyJWT

def read_public_key(filepath: str) -> str:
  with open(filepath, "r") as f:
    return f.read().strip()
  
JWT_PUBLIC_KEY = read_public_key("/app/oauth-tenant-public-key.pem")

def verify_token(request: Request, authorization: str = Header(title='authorization')):
  if not authorization:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth header")
  
  if not authorization.startswith("Bearer"):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
  
  token = authorization.split(" ")[1]

  try:
    payload = jwt.decode(jwt=token, key=JWT_PUBLIC_KEY, algorithms=["RS256"], audience="https://api.auratyme.com")
    request.state.userId = payload.get("sub")
    return payload
  except PyJWTError as err:
    print(err)
    
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Invalid or expired token",
    )
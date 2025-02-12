import React, { createContext, useMemo, useReducer, useEffect } from "react";
import {
  makeRedirectUri,
  useAuthRequest,
  useAutoDiscovery,
} from "expo-auth-session";
import { REACT_APP_KEYCLOAK_URL } from "@env";

const initialState = {
  isSignedIn: false,
  accessToken: null,
  idToken: null,
};

const AuthContext = createContext({
  state: initialState,
  signIn: () => {},
  signOut: () => {},
});
const AuthProvider = ({ children }) => {
  const discovery = useAutoDiscovery(
    `${REACT_APP_KEYCLOAK_URL}/realms/effective-day-ai`
  );
  const redirectUri = makeRedirectUri({
    useProxy: true,
  });
  const [request, response, promptAsync] = useAuthRequest(
    {
      clientId: "mobile-app",
      redirectUri: redirectUri,
      scopes: ["openid", "profile"],
    },
    discovery
  );
  const [authState, dispatch] = useReducer((previousState, action) => {
    switch (action.type) {
      case "SIGN_IN":
        return {
          ...previousState,
          isSignedIn: true,
          accessToken: action.payload.access_token,
          idToken: action.payload.id_token,
        };
      case "SIGN_OUT":
        return {
          ...initialState,
        };
    }
  }, initialState);

  const authContext = useMemo(
    () => ({
      state: authState,
      signIn: () => {
        promptAsync();
      },
      signOut: async () => {
        try {
          const idToken = authState.idToken;
          await fetch(
            `${REACT_APP_KEYCLOAK_URL}/realms/effective-day-ai/protocol/openid-connect/logout?id_token_hint=${idToken}`
          );
          dispatch({ type: "SIGN_OUT" });
        } catch (e) {
          console.warn(e);
        }
      },
    }),
    [authState]
  );

  useEffect(() => {
    const getToken = async ({ code, codeVerifier, redirectUri }) => {
      try {
        const formData = {
          grant_type: "authorization_code",
          client_id: "mobile-app",
          code: code,
          code_verifier: codeVerifier,
          redirect_uri: redirectUri,
        };
        const formBody = [];
        for (const property in formData) {
          var encodedKey = encodeURIComponent(property);
          var encodedValue = encodeURIComponent(formData[property]);
          formBody.push(encodedKey + "=" + encodedValue);
        }

        const response = await fetch(
          `${REACT_APP_KEYCLOAK_URL}/realms/effective-day-ai/protocol/openid-connect/token`,
          {
            method: "POST",
            headers: {
              Accept: "application/json",
              "Content-Type": "application/x-www-form-urlencoded",
            },
            body: formBody.join("&"),
          }
        );
        if (response.ok) {
          const payload = await response.json();
          dispatch({ type: "SIGN_IN", payload });
        }
      } catch (e) {
        console.warn(e);
      }
    };
    if (response?.type === "success") {
      const { code } = response.params;
      getToken({
        code,
        codeVerifier: request?.codeVerifier,
        redirectUri,
      });
    } else if (response?.type === "error") {
      console.warn("Authentication error: ", response.error);
    }
  }, [dispatch, redirectUri, request?.codeVerifier, response]);

  return (
    <AuthContext.Provider value={authContext}>{children}</AuthContext.Provider>
  );
};

export { AuthContext, AuthProvider };

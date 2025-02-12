import { Text, View, Button } from "react-native";
import React, { useContext } from "react";
import { AuthContext } from "./context/AuthContext";
import { Redirect } from "expo-router";

const App = () => {
  const { signIn, signOut, state } = useContext(AuthContext);

  return (
    <View style={{ flex: 1, justifyContent: "center", alignItems: "center" }}>
      <Text>SignIn-Screen</Text>
      <Button onPress={signIn} title={"Sign in"} />
      {state.isSignedIn ? (
        <Redirect href="/home"></Redirect>
      ) : (
        <Text>Nie jestes zalogowany</Text>
      )}
    </View>
  );
};

export default App;

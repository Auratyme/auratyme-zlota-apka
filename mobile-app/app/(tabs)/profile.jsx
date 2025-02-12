import React, { useContext } from "react";
import { AuthContext } from "../context/AuthContext";
import { Text, Button, View } from "react-native";
import { Redirect } from "expo-router";

function Profile() {
  const { signOut, state } = useContext(AuthContext);
  return (
    <View>
      <Text>Profile</Text>
      <Button onPress={signOut} title={"Wyloguj się"}></Button>
      {!state.isSignedIn && <Redirect href="/"></Redirect>}
    </View>
  );
}

export default Profile;

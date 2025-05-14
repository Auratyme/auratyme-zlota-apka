import { View, Image } from 'react-native';
import React from 'react';
import { useAuth0 } from 'react-native-auth0';
import { Redirect, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import placeholder from '@/assets/icons/profile-picture-placeholder.png';
import { Button, Text, Icon, FAB } from 'react-native-paper';
import { strings } from '../values';

const Profile = () => {
  const { user, clearCredentials, clearSession } = useAuth0();
  const router = useRouter();

  return (
    <SafeAreaView className="w-full h-full gap-10" style={{ padding: 20 }}>
      <View className="items-center">
        <Image
          source={user?.picture ? { uri: user.picture } : placeholder}
          className="rounded-full m-4"
          style={{ width: 150, height: 150 }}
          resizeMode="contain"
        />
        <Text className="my-4" variant="displaySmall">
          {user?.name}
        </Text>
      </View>
      <View className="mt-6 gap-4">
        <View style={{ display: 'flex', flexDirection: 'row', gap: 10 }}>
          <Icon source="account" size={25} />
          <Text variant="bodyLarge">{user?.name}</Text>
        </View>
        <View style={{ display: 'flex', flexDirection: 'row', gap: 10 }}>
          <Icon source="email" size={25} />
          <Text variant="bodyLarge">{user?.email}</Text>
        </View>
      </View>
      <Button
        mode="contained"
        icon="logout"
        onPress={async () => {
          try {
            await clearSession();
            await clearCredentials();
          } catch (e) {
            console.error(e);
          }
        }}
      >
        {strings.logoutButtonText}
      </Button>
      {!user && <Redirect href="/"></Redirect>}
      <FAB
        icon="information"
        onPress={() => {
          router.navigate('/info');
        }}
        style={{
          position: 'absolute',
          right: 0,
          bottom: 0,
          margin: 20,
        }}
      />
    </SafeAreaView>
  );
};

export default Profile;

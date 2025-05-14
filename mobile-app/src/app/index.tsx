import { View, Image } from 'react-native';

import { Redirect } from 'expo-router';
import { useAuth0 } from 'react-native-auth0';
import { Button, Text } from 'react-native-paper';

import backgroundImage from '@/assets/images/login-page-bg.png';
import { SafeAreaView } from 'react-native-safe-area-context';
import { strings } from '../values';
import { auth0 } from '../constants';

export default function Index() {
  const { user, authorize } = useAuth0();

  return (
    <SafeAreaView className="flex-col justify-center items-center">
      <Image
        source={backgroundImage}
        resizeMode="contain"
        style={{ width: 350, height: 350 }}
        className="self-center"
      />
      <View
        className="flex-column justify-center items-center"
        style={{
          marginVertical: 50,
        }}
      >
        <Text
          variant="displayMedium"
          style={{ padding: 10, textAlign: 'center' }}
        >
          {strings.loginScreenTitle}
        </Text>
        <Text
          variant="labelLarge"
          style={{ textAlign: 'center', maxWidth: 200 }}
        >
          {strings.loginScreenText}
        </Text>
      </View>
      <Button
        icon="login"
        mode="contained"
        onPress={async () => {
          try {
            await authorize({ audience: auth0.audience });
          } catch (e) {
            console.error(e);
          }
        }}
      >
        {strings.loginButtonText}
      </Button>
      {user && <Redirect href="/home"></Redirect>}
    </SafeAreaView>
  );
}

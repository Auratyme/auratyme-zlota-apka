import { useEffect } from 'react';

import { Stack, SplashScreen } from 'expo-router';
import { useFonts } from 'expo-font';
import { Auth0Provider } from 'react-native-auth0';

import '@/global.css';
import { auth0 } from '@/src/constants';
import { Header } from '@/src/components';
import { NotificationProvider } from '@/src/contexts';
import { useColorScheme } from 'react-native';
import { light, dark } from '@/theme.json';
import * as Notifications from 'expo-notifications';
import { PaperProvider, MD3DarkTheme, MD3Theme } from 'react-native-paper';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: false,
    shouldSetBadge: false,
  }),
});

export default function RootLayout() {
  const scheme = useColorScheme();
  const colors = scheme === 'dark' ? dark : light;
  const paperTheme: MD3Theme = {
    ...MD3DarkTheme,
    colors,
    dark: true,
    isV3: true,
  };

  const [fontsLoaded, error] = useFonts({
    'Poppins-Black': require('@/assets/fonts/Poppins-Black.ttf'),
    'Poppins-Bold': require('@/assets/fonts/Poppins-Bold.ttf'),
    'Poppins-ExtraBold': require('@/assets/fonts/Poppins-ExtraBold.ttf'),
    'Poppins-ExtraLight': require('@/assets/fonts/Poppins-ExtraLight.ttf'),
    'Poppins-Light': require('@/assets/fonts/Poppins-Light.ttf'),
    'Poppins-Medium': require('@/assets/fonts/Poppins-Medium.ttf'),
    'Poppins-Regular': require('@/assets/fonts/Poppins-Regular.ttf'),
    'Poppins-SemiBold': require('@/assets/fonts/Poppins-SemiBold.ttf'),
    'Poppins-Thin': require('@/assets/fonts/Poppins-Thin.ttf'),
  });

  useEffect(() => {
    if (error) console.error(error);

    if (fontsLoaded) {
      SplashScreen.hideAsync();
    }
  }, [fontsLoaded, error]);

  if (!fontsLoaded) {
    return null;
  }

  if (!fontsLoaded && !error) {
    return null;
  }

  return (
    <Auth0Provider domain={auth0.domain} clientId={auth0.clientId}>
      <NotificationProvider>
        <PaperProvider theme={paperTheme}>
          <Stack
            screenOptions={{
              navigationBarColor: colors.background,
              statusBarBackgroundColor: colors.background,
              contentStyle: {
                backgroundColor: colors.background,
              },
            }}
          >
            <Stack.Screen
              name="index"
              options={{
                headerShown: false,
              }}
            />
            <Stack.Screen name="(tabs)" options={{ header: Header }} />
            <Stack.Screen
              name="profile"
              options={{
                headerShown: false,
                animation: 'slide_from_right',
                statusBarAnimation: 'slide',
              }}
            />
            <Stack.Screen
              name="info"
              options={{
                headerShown: false,
                animation: 'slide_from_right',
                statusBarAnimation: 'slide',
              }}
            />
          </Stack>
        </PaperProvider>
      </NotificationProvider>
    </Auth0Provider>
  );
}

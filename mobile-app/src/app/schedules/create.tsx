import { View } from 'react-native';

import { Stack, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { strings } from '@/src/values';
import { schedulesApi } from '@/src/api';
import { useAuth0 } from 'react-native-auth0';
import { Button, TextInput } from 'react-native-paper';

export default function CreateScheduleScreen() {
  const { getCredentials } = useAuth0();

  const router = useRouter();
  const [token, setToken] = useState<string>('');
  const [name, setName] = useState<string>('');
  const [description, setDescription] = useState<string | null>(null);

  async function getToken() {
    try {
      const creds = await getCredentials();

      if (!creds) {
        throw new Error('Unable to get credentials');
      }
      setToken(creds.accessToken);
    } catch (error) {
      console.error(error);
    }
  }

  useEffect(() => {
    getToken();
  }, []);

  return (
    <View className="gap-8">
      <Stack.Screen
        name="create"
        options={{
          animation: 'slide_from_bottom',
          headerShown: false,
        }}
      />
      <TextInput
        mode="outlined"
        label={strings.createTaskScreenNameInputPlaceholder}
        maxLength={50}
        inputMode="text"
        onChangeText={(text) => {
          setName(text);
        }}
      />
      <TextInput
        mode="outlined"
        left={<TextInput.Icon icon="text" />}
        value={description || ''}
        maxLength={500}
        multiline={true}
        inputMode="text"
        onChangeText={(text) => {
          setDescription(text);
        }}
        label="Details"
      />
      <Button
        mode="contained"
        onPress={async () => {
          schedulesApi.create(
            {
              name: name,
              description: description || undefined,
            },
            token
          );

          router.replace('/schedules');
        }}
      >
        {strings.createScheduleButtonText}
      </Button>
    </View>
  );
}

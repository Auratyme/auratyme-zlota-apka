import { View } from 'react-native';

import { Stack, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { strings } from '@/src/values';
import { tasksApi } from '@/src/api';
import { useAuth0 } from 'react-native-auth0';
import { Button, Text, TextInput } from 'react-native-paper';
import { TimePickerModal, DatePickerModal } from 'react-native-paper-dates';
import { TaskRepetitionModal } from '@/src/components/common/modals';

export default function CreateTaskScreen() {
  const { getCredentials } = useAuth0();

  const router = useRouter();
  const [token, setToken] = useState<string>('');

  const [name, setName] = useState<string>('');
  const [description, setDescription] = useState<string | null>(null);
  const [dueDate, setDueDate] = useState<Date | null>(null);
  const [repeat, setRepeat] = useState<string | null>(null);

  const [modalShowed, setModalShowed] = useState<boolean>(false);
  const [timeModalVisible, setTimeModalVisible] = useState<boolean>(false);
  const [dateModalVisible, setDateModalVisible] = useState<boolean>(false);

  async function getToken() {
    try {
      const creds = await getCredentials();

      if (!creds || !creds.accessToken) {
        throw new Error('Nie udało się pobrać accessToken!');
      }
      setToken(creds.accessToken);
    } catch (error) {
      console.error('Auth0 error:', error);
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
          headerShown: false,
          animation: 'slide_from_bottom',
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
        className="flex-row justify-start"
        icon="calendar"
        onPress={() => {
          setDateModalVisible(true);
        }}
      >
        <Text variant="bodyLarge">
          {dueDate !== null
            ? new Date(dueDate).toLocaleDateString(undefined, {
                hour: '2-digit',
                minute: '2-digit',
                weekday: 'long',
                day: '2-digit',
                month: 'long',
              })
            : strings.createTaskScreenDateInputText}
        </Text>
      </Button>
      <Button
        className="flex-row gap-4"
        icon="repeat"
        onPress={() => {
          setModalShowed(true);
        }}
      >
        <Text variant="bodyLarge">
          {strings.createTaskScreenRepeatInputText}
        </Text>
      </Button>
      <Button
        mode="contained"
        onPress={async () => {
          tasksApi
            .create(
              {
                name,
                status: 'not-started',
                description: description,
                dueTo: dueDate?.toISOString() || null,
                repeat: repeat,
              },
              token
            )
            .then(() => {
              router.replace('/tasks');
            })
            .catch(console.error);
        }}
      >
        Create Task
      </Button>
      <TimePickerModal
        visible={timeModalVisible}
        use24HourClock
        onConfirm={(time) => {
          dueDate?.setHours(time.hours);
          dueDate?.setMinutes(time.minutes);
          dueDate?.setSeconds(0);
          setDueDate(dueDate);

          setTimeModalVisible(false);
        }}
        onDismiss={() => {
          setTimeModalVisible(false);
        }}
      />
      <DatePickerModal
        visible={dateModalVisible}
        onConfirm={(date) => {
          setDueDate(date.date || null);

          setDateModalVisible(false);
          setTimeModalVisible(true);
        }}
        onDismiss={() => {
          setDateModalVisible(false);
        }}
        mode="single"
        locale="pl"
      />
      <TaskRepetitionModal
        visible={modalShowed}
        onDismiss={() => {
          setModalShowed(false);
        }}
        onConfirm={(cron) => {
          setModalShowed(false);
          setRepeat(cron);
        }}
      />
    </View>
  );
}

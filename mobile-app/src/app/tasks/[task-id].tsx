import { Task as ITask, TaskStatus } from '@/src/types';
import { useLocalSearchParams, Stack } from 'expo-router';
import { View } from 'react-native';
import { useEffect, useState } from 'react';
import { tasksApi } from '@/src/api';
import { useAuth0 } from 'react-native-auth0';
import { strings } from '@/src/values';
import { DropDown } from '@/src/components/common';
import { ItemType } from 'react-native-dropdown-picker';
import { Text, TextInput, Button, Chip, IconButton } from 'react-native-paper';
import { TimePickerModal, DatePickerModal } from 'react-native-paper-dates';
import { TaskRepetitionModal } from '@/src/components/common/modals';

const dropdownOptions: ItemType<TaskStatus>[] = [
  { label: 'not started', value: 'not-started' },
  { label: 'done', value: 'done' },
  { label: 'failed', value: 'failed' },
  { label: 'in progress', value: 'in-progress' },
];

export default function TaskScreen() {
  const task = useLocalSearchParams<ITask>();

  const [token, setToken] = useState<string>('');
  const { getCredentials } = useAuth0();

  const [name, setName] = useState<string>(task.name);
  const [description, setDescription] = useState<string | null>(
    task.description
  );
  const [dueDate, setDueDate] = useState<Date | null>(
    task.dueTo ? new Date(task.dueTo) : null
  );
  const [repeat, setRepeat] = useState<string | null>(task.repeat);

  const [timeModalVisible, setTimeModalVisible] = useState<boolean>(false);
  const [dateModalVisible, setDateModalVisible] = useState<boolean>(false);
  const [repeatModalVisible, setRepeatModalVisible] = useState<boolean>(false);

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
        name="[task-id]"
        options={{
          headerShown: false,
          animation: 'slide_from_right',
        }}
      />
      <TextInput
        maxLength={50}
        label="Name"
        mode="outlined"
        value={name}
        onChangeText={(text) => {
          setName(text);
          tasksApi.updateOne(task.id, { name: text }, token);
        }}
      />
      <TextInput
        label="Details"
        mode="outlined"
        left={<TextInput.Icon icon="text" />}
        value={description || ''}
        maxLength={500}
        multiline={true}
        inputMode="text"
        onChangeText={(text) => {
          setDescription(text);
          tasksApi.updateOne(
            task.id,
            {
              description: text,
            },
            token
          );
        }}
      />
      <DropDown
        initialValue={task.status}
        onSelect={(item) => {
          tasksApi.updateOne(
            task.id,
            { status: item.value || task.status },
            token
          );
        }}
        options={dropdownOptions}
      />
      <View>
        <View className="flex-row items-center">
          <IconButton
            icon="calendar"
            className="flex-row"
            onPress={() => {
              setDateModalVisible(true);
            }}
          />
          {dueDate ? (
            <Chip
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
              closeIcon="close"
              onClose={() => {
                tasksApi
                  .updateOne(
                    task.id,
                    {
                      dueTo: null,
                    },
                    token
                  )
                  .then(() => {
                    setDueDate(null);
                  });
              }}
            >
              <Text variant="bodyLarge">
                {dueDate
                  ? new Date(dueDate).toLocaleDateString(undefined, {
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                  : strings.createTaskScreenDateInputText}
              </Text>
            </Chip>
          ) : (
            <Text variant="bodyLarge">Add due date</Text>
          )}
        </View>
        <View className="flex-row items-center">
          <IconButton
            icon="repeat"
            onPress={() => {
              setRepeatModalVisible(true);
            }}
          />
          {repeat ? (
            <Chip
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
              closeIcon="close"
              onClose={() => {
                tasksApi
                  .updateOne(
                    task.id,
                    {
                      repeat: null,
                    },
                    token
                  )
                  .then(() => {
                    setRepeat(null);
                  });
              }}
            >
              <Text>{repeat}</Text>
            </Chip>
          ) : (
            <Text variant="bodyLarge">Add repetiton</Text>
          )}
        </View>
      </View>
      <TimePickerModal
        visible={timeModalVisible}
        use24HourClock
        onConfirm={(time) => {
          const newDueDate = dueDate;

          newDueDate?.setHours(time.hours);
          newDueDate?.setMinutes(time.minutes);
          dueDate?.setSeconds(0);

          tasksApi
            .updateOne(
              task.id,
              {
                dueTo: newDueDate?.toISOString(),
              },
              token
            )
            .then(() => {
              setDueDate(newDueDate);

              setTimeModalVisible(false);
            });
        }}
        onDismiss={() => {
          setTimeModalVisible(false);
        }}
      />
      <DatePickerModal
        visible={dateModalVisible}
        onConfirm={(date) => {
          setDueDate(date.date ? date.date : null);

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
        visible={repeatModalVisible}
        onDismiss={() => {
          setRepeatModalVisible(false);
        }}
        onConfirm={(cron) => {
          tasksApi
            .updateOne(
              task.id,
              {
                repeat: cron,
              },
              token
            )
            .then(() => {
              setRepeat(cron);
              setRepeatModalVisible(false);
            });
        }}
      />
    </View>
  );
}

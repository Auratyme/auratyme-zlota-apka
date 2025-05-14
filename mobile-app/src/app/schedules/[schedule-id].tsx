import { Schedule as ISchedule, Task as ITask } from '@/src/types';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { View, FlatList, ScrollView } from 'react-native';
import { useEffect, useState } from 'react';
import { schedulesApi, tasksApi } from '@/src/api';
import { useAuth0 } from 'react-native-auth0';
import { Stack } from 'expo-router';
import {
  TextInput,
  useTheme,
  Checkbox,
  Text,
  Portal,
  Modal,
  Button,
} from 'react-native-paper';
import { TaskList } from '@/src/components';

type SmallTaskProps = {
  name: string;
  onChecked?: (checked: boolean) => void;
};

function SmallTask({ name, onChecked }: SmallTaskProps) {
  const [checked, setChecked] = useState<boolean>(false);

  return (
    <View
      style={{
        display: 'flex',
        flexDirection: 'row',
        gap: 4,
        alignItems: 'center',
      }}
    >
      <Checkbox
        status={checked ? 'checked' : 'unchecked'}
        onPress={() => {
          setChecked(!checked);

          if (onChecked) onChecked(checked);
        }}
      />
      <Text>{name}</Text>
    </View>
  );
}

type TasksModalProps = {
  visible: boolean;
  token: string;
  onDismiss?: () => void;
  onTaskCheck?: (task: ITask) => void;
  onTaskUncheck?: (task: ITask) => void;
  onAddBtnPress?: () => void;
};

function TasksModal({
  visible,
  token,
  onDismiss,
  onTaskCheck,
  onTaskUncheck,
  onAddBtnPress,
}: TasksModalProps) {
  const [tasks, setTasks] = useState<ITask[]>([]);
  const theme = useTheme();

  useEffect(() => {
    tasksApi.find(token).then((result) => setTasks(result));
  }, [visible]);

  return (
    <Portal>
      <Modal
        visible={visible}
        contentContainerStyle={{
          backgroundColor: theme.colors.background,
          padding: 20,
          margin: 20,
          display: 'flex',
          gap: 20,
        }}
        onDismiss={() => {
          if (onDismiss) onDismiss();
        }}
      >
        <Text variant="titleLarge" style={{ textAlign: 'center' }}>
          Tasks
        </Text>
        <FlatList
          data={tasks}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <SmallTask
              name={item.name}
              onChecked={(checked) => {
                if (checked && onTaskUncheck) {
                  onTaskUncheck(item);
                }

                if (!checked && onTaskCheck) {
                  onTaskCheck(item);
                }
              }}
            />
          )}
        />
        <Button mode="contained" onPress={onAddBtnPress}>
          Add
        </Button>
      </Modal>
    </Portal>
  );
}

export default function ScheduleScreen() {
  const schedule = useLocalSearchParams<ISchedule>();

  const [token, setToken] = useState<string>('');
  const { getCredentials } = useAuth0();
  const [description, setDescription] = useState<string | null>(
    schedule.description
  );
  const [name, setName] = useState<string>(schedule.name);
  const [modalShowed, setModalShowed] = useState<boolean>(false);
  const [selectedTasksIds, setSelectedTasksIds] = useState<string[]>([]);
  const [tasks, setTasks] = useState<ITask[]>([]);
  const theme = useTheme();
  const router = useRouter();

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

  useEffect(() => {
    schedulesApi
      .findTasks(schedule.id, {}, token)
      .then((result) => setTasks(result));
  }, [token]);

  useEffect(() => {
    setSelectedTasksIds([]);
  }, [modalShowed]);

  return (
    <View className="gap-8" style={{ flex: 1 }}>
      <Stack.Screen
        name="[schedule-id]"
        options={{
          animation: 'slide_from_right',
          headerShown: false,
        }}
      />
      <TextInput
        label="Name"
        maxLength={50}
        mode="outlined"
        value={name}
        onChangeText={(text) => {
          setName(text);
          schedulesApi.updateOne(schedule.id, { name: text }, token);
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
          schedulesApi.updateOne(
            schedule.id,
            {
              description: text,
            },
            token
          );
        }}
      />
      <Button
        mode="contained"
        onPress={() => {
          setModalShowed(true);
        }}
      >
        Add Task
      </Button>
      <TasksModal
        visible={modalShowed}
        token={token}
        onDismiss={() => {
          setModalShowed(false);

          schedulesApi.findTasks(schedule.id, {}, token).then((result) => {
            setTasks(result);
          });
        }}
        onTaskCheck={(task) => {
          setSelectedTasksIds([...selectedTasksIds, task.id]);
        }}
        onTaskUncheck={(task) => {
          setSelectedTasksIds(selectedTasksIds.filter((id) => task.id !== id));
        }}
        onAddBtnPress={() => {
          for (const id of selectedTasksIds) {
            schedulesApi.addTask(schedule.id, id, token);
          }

          setModalShowed(false);

          schedulesApi
            .findTasks(schedule.id, {}, token)
            .then((result) => setTasks(result));
        }}
      />
      <TaskList
        tasks={tasks}
        onDelete={(e, task) => {
          schedulesApi.removeTask(schedule.id, task.id, token).then(() => {
            setTasks(tasks.filter(({ id }) => task.id !== id));
          });
        }}
        onPress={(e, task) => {
          router.navigate({
            pathname: '/tasks/[task-id]',
            params: task,
          });
        }}
      />
    </View>
  );
}

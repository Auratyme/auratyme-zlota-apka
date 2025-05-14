import React, { useState, useEffect } from 'react';
import { View, Image } from 'react-native';

import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { cssInterop } from 'nativewind';
import { useFocusEffect } from '@react-navigation/native';
import { useAuth0 } from 'react-native-auth0';

import { TaskList } from '@/src/components';
import { Task as ITask } from '@/src/types';
import { tasksApi } from '@/src/api';
import { FAB, Text } from 'react-native-paper';
import sun from '@/assets/images/sun.png';

cssInterop(SafeAreaView, { className: 'style' });

export default function TasksScreen() {
  const router = useRouter();
  const { getCredentials } = useAuth0();
  const [token, setToken] = useState<string | null>(null);
  const [items, setItems] = useState<ITask[]>([]);

  useEffect(() => {
    getCredentials()
      .then((creds) => {
        if (!creds) {
          throw new Error('Unable to get credentials');
        }

        setToken(creds.accessToken);
      })
      .catch(console.error);
  }, []);

  const fetchData = async () => {
    const tasks = await tasksApi.find(token || '', {
      sortBy: 'asc',
      orderBy: 'dueTo',
    });

    setItems(tasks);
  };

  useFocusEffect(
    React.useCallback(() => {
      if (token) {
        fetchData();
      }
    }, [token])
  );

  return (
    <View className="h-full flex-1">
      <TaskList
        listEmptyComponent={
          <View className="items-center top-1/3">
            <Image source={sun} style={{ width: 200, height: 200 }} />
            <Text
              variant="titleLarge"
              style={{ textAlign: 'center' }}
              className="p-8"
            >
              Ready for a fresh start? Add your first task!
            </Text>
          </View>
        }
        tasks={items}
        onDelete={(e, item) => {
          tasksApi.deleteOne(item.id, token || '').then(() => {
            setItems(items.filter(({ id }) => item.id !== id));
          });
        }}
        onPress={(e, task) => {
          router.navigate({
            pathname: '/tasks/[task-id]',
            params: task,
          });
        }}
      />
      <FAB
        icon="plus"
        onPress={() => {
          router.navigate('/tasks/create');
        }}
        style={{
          position: 'absolute',
          right: 0,
          bottom: 0,
          margin: 20,
        }}
      />
    </View>
  );
}

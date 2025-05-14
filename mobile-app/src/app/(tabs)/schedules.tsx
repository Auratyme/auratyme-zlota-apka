import React, { useState, useEffect } from 'react';
import { View, Image } from 'react-native';

import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { cssInterop } from 'nativewind';
import { useFocusEffect } from '@react-navigation/native';
import { useAuth0 } from 'react-native-auth0';

import { ScheduleList } from '@/src/components';
import { Schedule as ISchedule } from '@/src/types';
import { schedulesApi } from '@/src/api';
import { FAB, Text } from 'react-native-paper';
import planner from '@/assets/images/planner.png';

cssInterop(SafeAreaView, { className: 'style' });

export default function SchedulesScreen() {
  const router = useRouter();
  const { getCredentials } = useAuth0();
  const [token, setToken] = useState<string | null>(null);
  const [items, setItems] = useState<ISchedule[]>([]);

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
    const schedules = await schedulesApi.find(token || '');

    setItems(schedules);
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
      <ScheduleList
        listEmptyComponent={
          <View className="items-center top-1/3">
            <Image source={planner} style={{ width: 200, height: 200 }} />
            <Text
              variant="titleLarge"
              style={{ textAlign: 'center' }}
              className="p-8"
            >
              Looking a little empty here. Add your schedules to stay organized.
            </Text>
          </View>
        }
        schedules={items}
        onDelete={(e, item) => {
          schedulesApi.deleteOne(item.id, token || '').then(() => {
            setItems(items.filter(({ id }) => item.id !== id));
          });
        }}
        onPress={(e, schedule) => {
          router.navigate({
            pathname: '/schedules/[schedule-id]',
            params: schedule,
          });
        }}
      />
      <FAB
        icon="plus"
        onPress={() => {
          router.navigate('/schedules/create');
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

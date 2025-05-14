import { GestureResponderEvent, View, FlatList } from 'react-native';

import { Schedule as ISchedule } from '@/src/types';

import Schedule from '../Schedule';
import { ReactElement } from 'react';

type ScheduleListProps = {
  schedules: ISchedule[];
  onDelete: (e: GestureResponderEvent, schedule: ISchedule) => void;
  onPress: (e: GestureResponderEvent, schedule: ISchedule) => void;
  listEmptyComponent?: ReactElement;
};

export default function ScheduleList({
  schedules,
  onDelete,
  onPress,
  listEmptyComponent,
}: ScheduleListProps) {
  return (
    <FlatList
      ListEmptyComponent={listEmptyComponent}
      data={schedules}
      keyExtractor={(item) => item.id}
      renderItem={({ item }) => (
        <Schedule
          schedule={item}
          onDelete={(e) => onDelete(e, item)}
          onPress={(e) => onPress(e, item)}
        />
      )}
    />
  );
}

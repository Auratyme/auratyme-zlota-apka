import { GestureResponderEvent, View, FlatList } from 'react-native';

import { ReactElement } from 'react';

import { Task as ITask } from '@/src/types';

import Task from '../Task';

type TaskListProps = {
  tasks: ITask[];
  onDelete: (e: GestureResponderEvent, task: ITask) => void;
  onPress: (e: GestureResponderEvent, task: ITask) => void;
  listEmptyComponent?: ReactElement;
};

export default function TaskList({
  tasks,
  onDelete,
  onPress,
  listEmptyComponent,
}: TaskListProps) {
  return (
    <FlatList
      ListEmptyComponent={listEmptyComponent}
      data={tasks}
      keyExtractor={(item) => item.id}
      renderItem={({ item }) => (
        <Task
          task={item}
          onDelete={(e) => onDelete(e, item)}
          onPress={(e) => onPress(e, item)}
        />
      )}
    />
  );
}

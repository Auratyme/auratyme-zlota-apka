import { GestureResponderEvent, StyleSheet, View } from 'react-native';

import { Task as ITask } from '@/src/types';

import { Card, useTheme, Text, IconButton, Icon } from 'react-native-paper';

type TaskProps = {
  task: ITask;
  onDelete: (e: GestureResponderEvent) => void;
  onPress: (e: GestureResponderEvent) => void;
};

export default function Task({ task, onDelete, onPress }: TaskProps) {
  const theme = useTheme();

  return (
    <Card onPress={onPress} style={styles.container}>
      <Card.Content style={styles.content}>
        <Text variant="titleMedium">{task.name}</Text>
        <Text>{task.status}</Text>
        {task.dueTo ? (
          <Text>
            {new Date(task.dueTo).toLocaleDateString(undefined, {
              hour: '2-digit',
              minute: '2-digit',
              weekday: 'long',
              day: '2-digit',
              month: 'long',
            })}
          </Text>
        ) : null}
        <View style={{ display: 'flex', flexDirection: 'row', gap: 4 }}>
          {task.description ? (
            <Icon source="text" size={15} color={theme.colors.primary} />
          ) : null}
          {task.dueTo ? (
            <Icon source="clock" size={15} color={theme.colors.primary} />
          ) : null}
          {task.repeat ? (
            <Icon source="repeat" size={15} color={theme.colors.primary} />
          ) : null}
        </View>
      </Card.Content>
      <Card.Actions>
        <IconButton
          icon="trash-can"
          onPress={onDelete}
          iconColor={theme.colors.error}
        />
      </Card.Actions>
    </Card>
  );
}

const styles = StyleSheet.create({
  content: {
    display: 'flex',
    gap: 8,
  },
  container: {
    margin: 8,
  },
});

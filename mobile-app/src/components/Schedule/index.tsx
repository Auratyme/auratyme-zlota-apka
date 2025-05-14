import { GestureResponderEvent, StyleSheet, View } from 'react-native';

import { Schedule as ISchedule } from '@/src/types';
import { Card, useTheme, Text, IconButton, Icon } from 'react-native-paper';

type ScheduleProps = {
  schedule: ISchedule;
  onDelete: (e: GestureResponderEvent) => void;
  onPress: (e: GestureResponderEvent) => void;
};

export default function Schedule({
  schedule,
  onDelete,
  onPress,
}: ScheduleProps) {
  const theme = useTheme();

  return (
    <Card style={styles.container} onPress={onPress}>
      <Card.Content style={styles.content}>
        <Text variant="titleMedium">{schedule.name}</Text>
        <View style={{ display: 'flex', flexDirection: 'row', gap: 4 }}>
          {schedule.description ? (
            <Icon source="text" size={15} color={theme.colors.primary} />
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

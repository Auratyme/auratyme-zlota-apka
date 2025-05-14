import { useTheme } from 'react-native-paper';
import { Stack } from 'expo-router';

export default function TasksLayout() {
  const theme = useTheme();

  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: {
          backgroundColor: theme.colors.background,
          padding: 20,
        },
      }}
    ></Stack>
  );
}

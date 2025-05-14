import { Tabs } from 'expo-router';
import { useTheme, Icon } from 'react-native-paper';

export default function TabsLayout() {
  const theme = useTheme();

  return (
    <>
      <Tabs
        screenOptions={{
          tabBarShowLabel: true,
          tabBarActiveTintColor: theme.colors.primary,
          tabBarInactiveTintColor: theme.colors.onSurface,
          tabBarStyle: {
            backgroundColor: theme.colors.surface,
          },
          headerShown: false,
          sceneStyle: {
            backgroundColor: theme.colors.background,
          },
          animation: 'shift',
        }}
      >
        <Tabs.Screen
          name="home"
          options={{
            title: 'Home',
            href: '/home',
            tabBarIcon: ({ color, focused }) => (
              <Icon source="home" size={20} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="tasks"
          options={{
            title: 'Tasks',
            href: '/tasks',
            tabBarIcon: ({ color, focused }) => (
              <Icon source="check" size={20} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="schedules"
          options={{
            title: 'Schedules',
            href: '/schedules',
            tabBarIcon: ({ color, focused }) => (
              <Icon source="calendar" size={20} color={color} />
            ),
          }}
        />
      </Tabs>
    </>
  );
}

import { useAuth0 } from 'react-native-auth0';
import { Link, useRouter } from 'expo-router';

import { strings } from '@/src/values';
import { Appbar } from 'react-native-paper';

export default function Header() {
  const { user } = useAuth0();
  const router = useRouter();

  if (!user) {
    return <Link href={{ pathname: '/' }} />;
  }

  return (
    <Appbar.Header>
      <Appbar.Content title={strings.appName} />
      <Appbar.Action
        icon="account-circle"
        onPress={() => {
          router.navigate({
            pathname: '/profile',
          });
        }}
      />
    </Appbar.Header>
  );
}

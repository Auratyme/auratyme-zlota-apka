import { Text } from 'react-native-paper';
import { View, ScrollView, SafeAreaView } from 'react-native';

export default function InfoScreen() {
  return (
    <ScrollView>
      <SafeAreaView>
        <View
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 40,
            padding: 30,
          }}
        >
          <View className="flex flex-col gap-4">
            <Text variant="headlineLarge">Czym jest Auratyme?</Text>
            <Text variant="bodyLarge">
              Auratyme to aplikacja wykorzystująca sztuczną inteligencję do
              zarządzania czasem. Analizuje dane użytkownika z urządzeń
              (smartfony, smartwatche, komputery) i na ich podstawie generuje
              spersonalizowane harmonogramy dnia. Uwzględnia priorytety, poziom
              energii i czas trwania zadań, pomagając w efektywnym planowaniu
              obowiązków i odpoczynku. Dzięki dynamicznej analizie danych
              dostosowuje harmonogram w czasie rzeczywistym, zwiększając
              produktywność i komfort codziennego życia. W efekcie użytkownicy
              zyskają narzędzie, które pomoże im lepiej organizować czas,
              ograniczyć stres związany z nadmiarem obowiązków i znaleźć
              równowagę między pracą a odpoczynkiem. Dzięki skutecznemu
              planowaniu będą bardziej efektywni, co przełoży się na lepsze
              samopoczucie i większą satysfakcję z codziennych działań. Docelowo
              aplikacja będzie dostępna na platformach mobilnych, umożliwiając
              szerokiemu gronu odbiorców lepsze zarządzanie swoim dniem.
            </Text>
          </View>
          <View className="flex flex-col gap-4">
            <Text variant="headlineLarge">Czy istnieją podobne aplikacje?</Text>
            <Text variant="bodyLarge">
              Istnieją narzędzia podobne do naszego. Są to m.in. Reclaim,
              Clockwise czy Trevor. Jednak wszystkie te aplikacje skupiają się
              na pracy i bardziej na reorganizowaniu podanego harmonogramu niż
              układaniu go. My idziemy krok dalej, zwracając uwagę na zdrowie i
              samopoczucie w tworzeniu list zadań. Nasz projekt ma za zadanie
              nie tylko ułatwić organizacje celów, ale również wspierać w ich
              spełnianiu, czego nie ma w innych narzędziach. Jedną z najbardziej
              innowacyjnych funkcji będzie integracja z urządzeniami wearable, z
              których to będą zbierane dane, co pozwoli na generowanie
              harmonogramów dopasowanych do potrzeb i życia użytkownika. To co
              tworzymy nie ogranicza się do aplikacji - jest to projekt mający
              na celu wsparcie ludzi w osiąganiu ich celów.
            </Text>
          </View>
          <View className="flex flex-col gap-4">
            <Text variant="headlineLarge">Plany na rozwój</Text>
            <Text variant="bodyLarge">
              Najważniejszą rzeczą, którą planujemy udoskonalać jest generowanie
              jak najlepszych harmonogramów, wykorzystując sztuczną inteligencją
              oraz dane z urządzeń wearable. Chcemy również dodać asystenta
              głosowego, który umożliwi bardzo szybkie i wygodne sterowanie
              aplikacją. Aby użytkownicy mogli łatwo monitorować swoje postępy
              dodamy statystyki oraz możliwość dodawania celów.
            </Text>
          </View>
        </View>
      </SafeAreaView>
    </ScrollView>
  );
}

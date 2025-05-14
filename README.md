# Wymagania

- zainstalowany docker
- zainstalowany nodejs (najnowsza wersja)
- komputer (na którym będzie uruchomiony backend) i telefon (na którym będzie uruchomiona aplikacja mobilna) muszą być w tej samej sieci (połączone z tym samym wifi)
- zainstalowana na telefonie aplikacja expo go (można ją pobrać ze sklepu play)

# Jak uruchomić

## Backend

1. wejść do folderu backend (`cd .\backend`)
2. uruchomić w nim skrypt startup-win.bat (`.\startup-win.bat`)

## Aplikacja mobilna

1. wejść do folderu mobile-app
2. utworzyć w nim plik .env
3. w pliku .env dodać zmienną środowiskową `EXPO_PUBLIC_API_URL` i przypisać do niej wartość adresu IPV4 sieci, do której obecnie jest podłączony komputer, na którym działa backend (można go zobaczyć posługując się komendą `ipconfig`). Linia wpisana do pliku powinna być w takim formacie: `EXPO_PUBLIC_API_URL=<adres_ipv4>` (bez ostrych nawiasów).
4. potem należy pobrać, skompilowaną wersję aplikacji z tego: [linku](https://expo.dev/accounts/kamilabbasi/projects/auratyme-mobile/builds/bd92b5c0-0060-4423-95e0-e796bf99bb6b) (należy kliknąć przycisk `install`)
5. następnie (nadal w folderze mobile-app) należy wykonać komendy: `npm i`, a potem `npm run start:no-cache`
6. Po wykonaniu obu tych komend należy zeskanować kod QR, korzystając z aplikacji expo go.

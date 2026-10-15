# Zgrywanie Memory Stick — szybki start

Ten projekt dotyczy **Sony MSAC-US1, USB `054c:002d`, oraz starej karty Memory Stick 32 MB**. Nie jest uniwersalnym sterownikiem do wszystkich czytników. Pliki są kopiowane bez zmiany jakości i bez kasowania karty.

## Windows

1. Pobierz ZIP z GitHuba: **Code → Download ZIP**. Rozpakuj na lokalnym dysku.
2. Przeczytaj [instrukcję Windows](windows.md). Pierwsza konfiguracja wymaga Ubuntu WSL2 i uprawnień administratora. Nie wykonuj jej na cudzym komputerze bez zgody właściciela.
3. W PowerShell uruchom `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\windows\Setup-Windows.ps1`, aby sprawdzić wymagania.
4. Gdy chcesz zainstalować usługę USB/IP i przypisać czytnik, uruchom PowerShell jako administrator i wykonaj `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\windows\Setup-Windows.ps1 -InstallUsbipd -ConfigureReader`.
5. Na co dzień: włóż kartę, podłącz czytnik do skonfigurowanego portu i kliknij dwukrotnie **`windows/Import Memory Stick.cmd`**. Możesz utworzyć do tego pliku skrót na pulpicie.

Kopie trafiają do folderu **Obrazy → MemoryStick-Backups**, osobno dla każdego zgrywania. Zielony komunikat potwierdza sprawdzenie plików i odłączenie odczytu. Przy błędzie nie czyść karty; jeśli program nie potwierdzi zakończenia odczytu, pozostaw czytnik do sprawdzenia.

## Mac

Uruchom `python3 macos/diagnose.py` i zobacz [stan obsługi macOS](macos.md). To diagnostyka, nie działający importer. Wykrycie czytnika przez USB nie oznacza, że macOS potrafi odczytać kartę. Wersja macOS wymaga osobnego testu sprzętowego; nie instaluj starych sterowników Sony z przypadkowych stron ani nie wyłączaj zabezpieczeń systemu.

## Linux

Zobacz [instrukcję Linux](linux.md). Importer ustawia odczyt tylko do odczytu i sprawdza SHA-256. Nie wybieraj ręcznie losowego `/dev/sdX`.

## Przed wyjazdem

Pobierz projekt i potrzebne oficjalne instalatory wcześniej, sprawdź działanie na docelowym komputerze i zachowaj kopię poza kartą. Pierwsze przygotowanie Windows/maszyny Linux nie jest natychmiastowe. Na komputerze bez uprawnień administratora lub z blokadą instalacji może być niemożliwe.

Po imporcie otwórz zdjęcia/filmy. Dopiero po sprawdzeniu kopii rozważ wyczyszczenie karty w kamerze. Projekt niczego nie usuwa. Memory Stick w DCR-TRV20E służy do zdjęć; kasety MiniDV wymagają osobnej procedury zgrywania.

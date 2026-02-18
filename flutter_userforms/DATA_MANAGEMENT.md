# Form Data Management

This Flutter app loads form options (organizations, programs, concentrations) from text files instead of hardcoding them.

## 📁 File Structure

```
flutter_userforms/
├── assets/
│   └── data/               # Text files with form data
│       ├── ncsu_orgs.txt
│       ├── undergrad_programs.txt
│       ├── grad_programs.txt
│       └── concentrations.txt
├── lib/
│   └── services/
│       └── form_data_loader.dart  # Service that loads text files
```

## 🔄 How It Works

1. **Python Script Generates Data** (run once)
   - `pullorgs.py` fetches organizations from NCSU API
   - Outputs to `data/ncsu_orgs.txt` in the project root
   
2. **Copy to Flutter Assets**
   - Text files must be in `flutter_userforms/assets/data/`
   - Run `./copy_data.sh` to sync from `data/` to `assets/data/`

3. **Flutter Loads at Startup**
   - `FormDataLoader` service reads all .txt files
   - Data is cached in memory for the app session
   - Loading screen shows while data loads

## 📝 Text File Format

Each file should have **one option per line**:

```
Computer Engineering
Electrical Engineering
Electrical and Computer Engineering
```

Blank lines and extra whitespace are automatically trimmed.

## 🔧 Adding New Data Files

1. **Create the text file:**
   ```bash
   # In flutter_userforms/assets/data/
   echo "Option 1\nOption 2\nOption 3" > new_data.txt
   ```

2. **Update pubspec.yaml:**
   ```yaml
   flutter:
     assets:
       - assets/data/new_data.txt
   ```

3. **Add loader method in `form_data_loader.dart`:**
   ```dart
   List<String>? _newData;
   
   Future<List<String>> loadNewData() async {
     if (_newData != null) return _newData!;
     final data = await rootBundle.loadString('assets/data/new_data.txt');
     _newData = data.split('\n')
       .map((line) => line.trim())
       .where((line) => line.isNotEmpty)
       .toList();
     return _newData!;
   }
   
   List<String> get newData => _newData ?? [];
   ```

4. **Call in `loadAll()`:**
   ```dart
   await Future.wait([
     // ... existing loaders
     loadNewData(),
   ]);
   ```

5. **Add getter in `form_options.dart`:**
   ```dart
   static List<String> get newData => _loader.newData;
   ```

## 🔄 Updating Organizations

When organizations change:

1. **Run Python script** (in project root):
   ```bash
   cd /path/to/AI-Ind-Study
   python pullorgs.py
   # Creates/updates data/ncsu_orgs.txt
   ```

2. **Copy to Flutter assets**:
   ```bash
   cd flutter_userforms
   ./copy_data.sh
   ```

3. **Rebuild app**:
   ```bash
   flutter run
   ```

The app automatically loads the new data on next launch!

## 📊 Current Data Files

| File | Purpose | Source |
|------|---------|--------|
| `ncsu_orgs.txt` | Student organizations | `pullorgs.py` API fetch |
| `undergrad_programs.txt` | BS degree programs | Manual |
| `grad_programs.txt` | MS/PhD programs | Manual |
| `concentrations.txt` | Specializations | Manual |

## 🎯 Benefits

✅ No need to rebuild app to update organizations  
✅ Python script handles data collection  
✅ Flutter just reads the files  
✅ Easy to maintain and update  
✅ Can add new data types anytime  

## ⚠️ Important Notes

- Text files must be in `assets/data/` (not the root `data/` folder!)
- All assets must be declared in `pubspec.yaml`
- App shows loading screen while files are read
- Data is cached after first load (fast!)
- Empty lines and whitespace are automatically cleaned up

import 'package:flutter/material.dart';
import 'package:fuzzywuzzy/fuzzywuzzy.dart';
import '../constants/form_options.dart';
import '../services/organization_search_service.dart';

/// Reusable UI builders for the mentee interest form.
class FormFieldWidgets {
  /// Section title with bottom divider.
  static Widget buildSection(BuildContext context, String title) {
    return Container(
      padding: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(color: Theme.of(context).dividerColor, width: 2),
        ),
      ),
      child: Text(
        title,
        style: Theme.of(
          context,
        ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
      ),
    );
  }

  /// Labeled single-line text field.
  static Widget buildTextField(
    BuildContext context,
    TextEditingController controller,
    String label,
    bool required,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '$label${required ? ' *' : ''}',
          style: Theme.of(
            context,
          ).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          decoration: InputDecoration(
            hintText: 'Enter your $label',
            border: const OutlineInputBorder(),
          ),
        ),
      ],
    );
  }

  /// NCSU email field with helper message.
  static Widget buildEmailField(
    BuildContext context,
    TextEditingController controller,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Email address *',
          style: Theme.of(
            context,
          ).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 4),
        Text(
          'Please make sure to use your NCSU email',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Theme.of(context).colorScheme.error,
            fontStyle: FontStyle.italic,
          ),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          keyboardType: TextInputType.emailAddress,
          decoration: const InputDecoration(
            hintText: 'your.name@ncsu.edu',
            border: OutlineInputBorder(),
            prefixIcon: Icon(Icons.email),
          ),
        ),
      ],
    );
  }

  /// Pronoun chooser.
  static Widget buildPronounsField(
    BuildContext context,
    List<String> selectedPronouns,
    Function(List<String>) onChanged,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Pronouns *',
          style: Theme.of(
            context,
          ).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: FormOptions.pronouns.map((pronoun) {
            final isSelected = _containsOptionSelection(
              selectedPronouns,
              pronoun,
            );
            return FilterChip(
              label: Text(pronoun),
              selected: isSelected,
              onSelected: (selected) {
                final updated = List<String>.from(selectedPronouns);
                if (selected) {
                  if (!_containsOptionSelection(updated, pronoun)) {
                    updated.add(pronoun);
                  }
                } else {
                  updated.removeWhere(
                    (value) => _optionMatchesSelection(value, pronoun),
                  );
                }
                onChanged(updated);
              },
            );
          }).toList(),
        ),
        if (selectedPronouns.isNotEmpty) ...[
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: selectedPronouns.map((value) {
              return Chip(
                label: Text(value),
                onDeleted: () {
                  final updated = List<String>.from(selectedPronouns)
                    ..remove(value);
                  onChanged(updated);
                },
              );
            }).toList(),
          ),
        ],
      ],
    );
  }

  /// Education level selector.
  static Widget buildEducationLevelField(
    BuildContext context,
    String? selectedLevel,
    Function(String?) onChanged,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Current education level *',
          style: Theme.of(
            context,
          ).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 4),
        Text(
          'Select the degree(s) you are currently pursuing',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Theme.of(context).hintColor,
            fontStyle: FontStyle.italic,
          ),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: FormOptions.educationLevels.map((level) {
            String displayLabel = level;
            if (level == 'BS') {
              displayLabel = 'BS (Bachelor of Science)';
            }
            if (level == 'MS') {
              displayLabel = 'MS (Master of Science)';
            }
            if (level == 'ABM') {
              displayLabel = 'ABM (Accelerated Bachelor\'s/Master\'s)';
            }

            return ChoiceChip(
              label: Text(displayLabel),
              selected: selectedLevel == level,
              onSelected: (selected) {
                onChanged(selected ? level : null);
              },
              backgroundColor: Colors.grey[100],
              selectedColor: Theme.of(context).colorScheme.primaryContainer,
            );
          }).toList(),
        ),
      ],
    );
  }

  /// Graduation date selector (semester + year).
  static Widget buildGraduationDateField(
    BuildContext context,
    String? selectedSemester,
    String? selectedYear,
    Function(String?) onSemesterChanged,
    Function(String?) onYearChanged,
  ) {
    final years = FormOptions.getGraduationYears();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Expected graduation date *',
          style: Theme.of(
            context,
          ).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              flex: 2,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Semester',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 8),
                  DropdownButtonFormField<String>(
                    initialValue: selectedSemester,
                    decoration: InputDecoration(
                      border: const OutlineInputBorder(),
                      hintText: 'Select',
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 16,
                      ),
                      filled: true,
                      fillColor: Colors.grey[50],
                    ),
                    items: FormOptions.semester.map((semester) {
                      return DropdownMenuItem(
                        value: semester,
                        child: Text(semester),
                      );
                    }).toList(),
                    onChanged: onSemesterChanged,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              flex: 1,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Year',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 8),
                  DropdownButtonFormField<String>(
                    initialValue: selectedYear,
                    decoration: InputDecoration(
                      border: const OutlineInputBorder(),
                      hintText: 'Year',
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 16,
                      ),
                      filled: true,
                      fillColor: Colors.grey[50],
                    ),
                    items: years.map((year) {
                      return DropdownMenuItem(value: year, child: Text(year));
                    }).toList(),
                    onChanged: onYearChanged,
                  ),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }

  /// Scrollable multi-select for degree programs by education level.
  static Widget buildDegreeProgramField(
    BuildContext context,
    String? educationLevel,
    List<String> selectedPrograms,
    Function(List<String>) onChanged,
  ) {
    final programs = List<String>.from(
      FormOptions.getDegreeProgramsForLevel(educationLevel),
    );
    if (!programs.any((item) => item.trim().toLowerCase() == 'other')) {
      programs.add('Other');
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Degree program(s) *',
          style: Theme.of(
            context,
          ).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 4),
        if (educationLevel == null)
          Padding(
            padding: const EdgeInsets.only(top: 4, bottom: 8),
            child: Text(
              'Please select your education level first',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.error,
                fontStyle: FontStyle.italic,
              ),
            ),
          )
        else
          Padding(
            padding: const EdgeInsets.only(top: 4, bottom: 8),
            child: Text(
              educationLevel == 'BS'
                  ? 'Undergraduate ECE programs'
                  : educationLevel == 'ABM'
                  ? 'ABM programs'
                  : educationLevel == 'MS'
                  ? 'Graduate ECE programs'
                  : 'PhD programs',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).hintColor,
                fontStyle: FontStyle.italic,
              ),
            ),
          ),
        Container(
          height: 220,
          decoration: BoxDecoration(
            border: Border.all(color: Theme.of(context).dividerColor),
            borderRadius: BorderRadius.circular(8),
            color: Colors.grey[50],
          ),
          child: educationLevel == null
              ? Center(
                  child: Text(
                    'Select education level to view programs',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).hintColor,
                    ),
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  itemCount: programs.length,
                  itemBuilder: (context, index) {
                    final program = programs[index];
                    final isSelected = _containsOptionSelection(
                      selectedPrograms,
                      program,
                    );

                    return CheckboxListTile(
                      dense: true,
                      controlAffinity: ListTileControlAffinity.leading,
                      title: Text(program),
                      value: isSelected,
                      onChanged: (selected) {
                        final next = List<String>.from(selectedPrograms);
                        if (selected == true) {
                          if (!_containsOptionSelection(next, program)) {
                            next.add(program);
                          }
                        } else {
                          next.removeWhere(
                            (value) => _optionMatchesSelection(value, program),
                          );
                        }
                        onChanged(next);
                      },
                    );
                  },
                ),
        ),
        const SizedBox(height: 6),
        Text(
          'Selected: ${selectedPrograms.length}',
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: Theme.of(context).hintColor),
        ),
        if (selectedPrograms.isNotEmpty) ...[
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: selectedPrograms.map((value) {
              return Chip(
                label: Text(value),
                onDeleted: () {
                  final next = List<String>.from(selectedPrograms)
                    ..remove(value);
                  onChanged(next);
                },
              );
            }).toList(),
          ),
        ],
      ],
    );
  }

  /// Optional concentration selector (toggle + dialog with fuzzy search).
  static Widget buildConcentrationField(
    BuildContext context,
    bool hasConcentration,
    List<String> selectedConcentrations,
    List<String> options,
    Function(bool) onToggle,
    Function(List<String>) onSelected,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        CheckboxListTile(
          value: hasConcentration,
          controlAffinity: ListTileControlAffinity.leading,
          title: const Text('Do you have a concentration?'),
          onChanged: (value) => onToggle(value ?? false),
        ),
        if (hasConcentration) ...[
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: Text(
                  'Selected: ${selectedConcentrations.length} concentration(s)',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).hintColor,
                  ),
                ),
              ),
              TextButton.icon(
                onPressed: () => _showConcentrationDialog(
                  context,
                  options,
                  selectedConcentrations,
                  onSelected,
                ),
                icon: const Icon(Icons.search),
                label: const Text('Search & select'),
              ),
            ],
          ),
          if (selectedConcentrations.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: selectedConcentrations.map((c) {
                return Chip(
                  label: Text(c),
                  onDeleted: () {
                    final next = List<String>.from(selectedConcentrations)
                      ..remove(c);
                    onSelected(next);
                  },
                );
              }).toList(),
            ),
          ],
        ],
      ],
    );
  }

  /// Free-form specialization text for PhD selections.
  static Widget buildPhdSpecializationField(
    BuildContext context,
    TextEditingController controller,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'PhD specialization *',
          style: Theme.of(
            context,
          ).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          decoration: const InputDecoration(
            hintText: 'e.g., Power systems, ML hardware, communications',
            border: OutlineInputBorder(),
          ),
        ),
      ],
    );
  }

  /// Build multi-select filter chips
  static Widget buildMultiSelectChips(
    BuildContext context,
    String label,
    String helperText,
    List<String> options,
    List<String> selectedOptions,
    Function(List<String>) onChanged,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: Theme.of(
            context,
          ).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 4),
        Text(
          helperText,
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: Theme.of(context).hintColor),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: options.map((option) {
            final isSelected = _containsOptionSelection(
              selectedOptions,
              option,
            );
            return FilterChip(
              label: Text(option),
              selected: isSelected,
              onSelected: (selected) {
                final newSelection = List<String>.from(selectedOptions);
                if (selected) {
                  if (!_containsOptionSelection(newSelection, option)) {
                    newSelection.add(option);
                  }
                } else {
                  newSelection.removeWhere(
                    (value) => _optionMatchesSelection(value, option),
                  );
                }
                onChanged(newSelection);
              },
            );
          }).toList(),
        ),
        if (selectedOptions.isNotEmpty) ...[
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: selectedOptions.map((value) {
              return Chip(
                label: Text(value),
                onDeleted: () {
                  final updated = List<String>.from(selectedOptions)
                    ..remove(value);
                  onChanged(updated);
                },
              );
            }).toList(),
          ),
        ],
      ],
    );
  }

  /// Build single-select choice chips
  static Widget buildSingleSelectChips(
    BuildContext context,
    String label,
    String? helperText,
    List<String> options,
    String? selectedOption,
    Function(String?) onChanged,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: Theme.of(
            context,
          ).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
        ),
        if (helperText != null) ...[
          const SizedBox(height: 4),
          Text(
            helperText,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Theme.of(context).hintColor,
              fontStyle: FontStyle.italic,
            ),
          ),
        ],
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: options.map((option) {
            return ChoiceChip(
              label: Text(option),
              selected: selectedOption == option,
              onSelected: (selected) {
                onChanged(selected ? option : null);
              },
            );
          }).toList(),
        ),
      ],
    );
  }

  /// Build yes/no custom radio buttons
  static Widget buildYesNoField(
    BuildContext context,
    String label,
    bool? selectedValue,
    Function(bool?) onChanged,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: Theme.of(
            context,
          ).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: InkWell(
                onTap: () => onChanged(true),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    vertical: 12,
                    horizontal: 16,
                  ),
                  decoration: BoxDecoration(
                    border: Border.all(
                      color: selectedValue == true
                          ? Theme.of(context).colorScheme.primary
                          : Colors.grey.shade300,
                      width: selectedValue == true ? 2 : 1,
                    ),
                    borderRadius: BorderRadius.circular(8),
                    color: selectedValue == true
                        ? Theme.of(
                            context,
                          ).colorScheme.primaryContainer.withValues(alpha: 0.3)
                        : Colors.transparent,
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        selectedValue == true
                            ? Icons.radio_button_checked
                            : Icons.radio_button_unchecked,
                        color: selectedValue == true
                            ? Theme.of(context).colorScheme.primary
                            : Colors.grey,
                      ),
                      const SizedBox(width: 8),
                      const Text('Yes'),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: InkWell(
                onTap: () => onChanged(false),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    vertical: 12,
                    horizontal: 16,
                  ),
                  decoration: BoxDecoration(
                    border: Border.all(
                      color: selectedValue == false
                          ? Theme.of(context).colorScheme.primary
                          : Colors.grey.shade300,
                      width: selectedValue == false ? 2 : 1,
                    ),
                    borderRadius: BorderRadius.circular(8),
                    color: selectedValue == false
                        ? Theme.of(
                            context,
                          ).colorScheme.primaryContainer.withValues(alpha: 0.3)
                        : Colors.transparent,
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        selectedValue == false
                            ? Icons.radio_button_checked
                            : Icons.radio_button_unchecked,
                        color: selectedValue == false
                            ? Theme.of(context).colorScheme.primary
                            : Colors.grey,
                      ),
                      const SizedBox(width: 8),
                      const Text('No'),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  /// Build organizations searchable multi-select
  static Widget buildOrganizationsField(
    BuildContext context,
    List<String> selectedOrgs,
    Function(List<String>) onChanged,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Student organizations and clubs',
          style: Theme.of(
            context,
          ).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 4),
        Text(
          'Select all that you are involved with',
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: Theme.of(context).hintColor),
        ),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            border: Border.all(color: Theme.of(context).dividerColor),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Selected: ${selectedOrgs.length} organization(s)',
                style: Theme.of(
                  context,
                ).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w500),
              ),
              const SizedBox(height: 8),
              TextButton.icon(
                onPressed: () =>
                    _showOrgsDialog(context, selectedOrgs, onChanged),
                icon: const Icon(Icons.search),
                label: const Text('Search and select organizations'),
              ),
              if (selectedOrgs.isNotEmpty) ...[
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: selectedOrgs.map((org) {
                    return Chip(
                      label: Text(org),
                      onDeleted: () {
                        final newList = List<String>.from(selectedOrgs);
                        newList.remove(org);
                        onChanged(newList);
                      },
                    );
                  }).toList(),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }

  /// Show organizations dialog
  static void _showOrgsDialog(
    BuildContext context,
    List<String> currentSelection,
    Function(List<String>) onChanged,
  ) {
    final searchService = OrganizationSearchService.shared;
    showDialog(
      context: context,
      builder: (context) {
        List<String> tempSelected = List.from(currentSelection);
        String searchQuery = '';
        List<String> results = FormOptions.ncsuOrgs;
        bool loading = false;

        return StatefulBuilder(
          builder: (context, setDialogState) {
            final filteredOrgs = results;

            return AlertDialog(
              title: const Text('Select Organizations'),
              content: SizedBox(
                width: double.maxFinite,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextField(
                      decoration: const InputDecoration(
                        hintText: 'Search organizations...',
                        prefixIcon: Icon(Icons.search),
                        border: OutlineInputBorder(),
                      ),
                      onChanged: (value) {
                        searchQuery = value;
                        setDialogState(() => loading = true);
                        searchService
                            .search(searchQuery, FormOptions.ncsuOrgs)
                            .then((merged) {
                              if (!context.mounted) return;
                              setDialogState(() {
                                results = merged;
                                loading = false;
                              });
                            });
                      },
                    ),
                    const SizedBox(height: 16),
                    if (loading) const LinearProgressIndicator(),
                    if (loading) const SizedBox(height: 8),
                    Expanded(
                      child: ListView.builder(
                        shrinkWrap: true,
                        itemCount: filteredOrgs.length,
                        itemBuilder: (context, index) {
                          final org = filteredOrgs[index];
                          final isSelected = tempSelected.contains(org);

                          return CheckboxListTile(
                            title: Text(org),
                            value: isSelected,
                            onChanged: (selected) {
                              setDialogState(() {
                                if (selected == true) {
                                  tempSelected.add(org);
                                } else {
                                  tempSelected.remove(org);
                                }
                              });
                            },
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () {
                    onChanged(tempSelected);
                    Navigator.pop(context);
                  },
                  child: const Text('Done'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  /// Show concentrations dialog with fuzzy search.
  static void _showConcentrationDialog(
    BuildContext context,
    List<String> allOptions,
    List<String> currentSelection,
    Function(List<String>) onSelected,
  ) {
    showDialog(
      context: context,
      builder: (context) {
        List<String> tempSelected = List.from(currentSelection);
        String searchQuery = '';

        return StatefulBuilder(
          builder: (context, setDialogState) {
            final filtered = _filterOptionsFuzzy(
              searchQuery,
              allOptions,
              limit: 40,
            );

            return AlertDialog(
              title: const Text('Select concentrations'),
              content: SizedBox(
                width: double.maxFinite,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextField(
                      decoration: const InputDecoration(
                        hintText: 'Search concentrations...',
                        prefixIcon: Icon(Icons.search),
                        border: OutlineInputBorder(),
                      ),
                      onChanged: (value) =>
                          setDialogState(() => searchQuery = value),
                    ),
                    const SizedBox(height: 16),
                    Expanded(
                      child: ListView.builder(
                        shrinkWrap: true,
                        itemCount: filtered.length,
                        itemBuilder: (context, index) {
                          final opt = filtered[index];
                          final isSelected = tempSelected.contains(opt);
                          return CheckboxListTile(
                            title: Text(opt),
                            value: isSelected,
                            onChanged: (selected) {
                              setDialogState(() {
                                if (selected == true) {
                                  tempSelected.add(opt);
                                } else {
                                  tempSelected.remove(opt);
                                }
                              });
                            },
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () {
                    onSelected(tempSelected);
                    Navigator.pop(context);
                  },
                  child: const Text('Done'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  /// Fuzzy + substring filter helper (keeps reasonable limit).
  static List<String> _filterOptionsFuzzy(
    String query,
    List<String> options, {
    int limit = 50,
  }) {
    final trimmed = query.trim();
    if (trimmed.isEmpty) {
      return options.take(limit).toList();
    }

    final results = extractAllSorted(
      query: trimmed,
      choices: options,
      cutoff: 30,
    );

    // Fallback to simple contains if fuzzy yields nothing
    if (results.isEmpty) {
      return options
          .where((o) => o.toLowerCase().contains(trimmed.toLowerCase()))
          .take(limit)
          .toList();
    }

    return results.map((r) => r.choice).take(limit).toList();
  }

  /// Build multi-line text field
  static Widget buildMultiLineTextField(
    BuildContext context,
    TextEditingController controller,
    String label,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: Theme.of(
            context,
          ).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          maxLines: 5,
          decoration: const InputDecoration(
            hintText:
                'Share your story, interests, goals, or anything else you\'d like your mentor to know...',
            border: OutlineInputBorder(),
          ),
        ),
      ],
    );
  }

  /// Build matching priorities info box
  static Widget buildMatchingPrioritiesInfo(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(
          context,
        ).colorScheme.primaryContainer.withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Rate the importance of the following when matching you with a mentor:',
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          Text(
            '1 = Not important | 2 = Slightly important | 3 = Important | 4 = Very important',
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: Theme.of(context).hintColor),
          ),
        ],
      ),
    );
  }

  /// Build Likert scale slider
  static Widget buildLikertScale(
    BuildContext context,
    String label,
    double value,
    Function(double) onChanged,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w500),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Text('1', style: Theme.of(context).textTheme.bodySmall),
            Expanded(
              child: Slider(
                value: value,
                min: 1,
                max: 4,
                divisions: 3,
                label: value.round().toString(),
                onChanged: onChanged,
              ),
            ),
            Text('4', style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
        Center(
          child: Text(
            FormOptions.getLikertLabel(value.round()),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Theme.of(context).colorScheme.primary,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
      ],
    );
  }

  static bool _containsOptionSelection(List<String> selected, String option) {
    return selected.any((value) => _optionMatchesSelection(value, option));
  }

  static bool _optionMatchesSelection(String selectedValue, String option) {
    final selectedNormalized = selectedValue.trim().toLowerCase();
    final optionNormalized = option.trim().toLowerCase();

    if (optionNormalized == 'other') {
      return selectedNormalized == 'other' ||
          selectedNormalized.startsWith('other:');
    }
    return selectedValue == option;
  }
}

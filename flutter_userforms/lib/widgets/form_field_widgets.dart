import 'package:flutter/material.dart';
import '../constants/form_options.dart';

/// Reusable form field widgets for the mentee interest form
class FormFieldWidgets {
  /// Build a section header with divider
  static Widget buildSection(BuildContext context, String title) {
    return Container(
      padding: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(
            color: Theme.of(context).dividerColor,
            width: 2,
          ),
        ),
      ),
      child: Text(
        title,
        style: Theme.of(context).textTheme.headlineSmall?.copyWith(
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  /// Build a generic text field
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
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            fontWeight: FontWeight.w600,
          ),
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

  /// Build email field with validation hint
  static Widget buildEmailField(
    BuildContext context,
    TextEditingController controller,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Email address *',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            fontWeight: FontWeight.w600,
          ),
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

  /// Build pronouns choice chips
  static Widget buildPronounsField(
    BuildContext context,
    String? selectedPronoun,
    Function(String?) onChanged,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Pronouns *',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: FormOptions.pronouns.map((pronoun) {
            return ChoiceChip(
              label: Text(pronoun),
              selected: selectedPronoun == pronoun,
              onSelected: (selected) {
                onChanged(selected ? pronoun : null);
              },
            );
          }).toList(),
        ),
      ],
    );
  }

  /// Build education level field with helper text
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
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            fontWeight: FontWeight.w600,
          ),
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
            if (level == 'BS') displayLabel = 'BS (Bachelor of Science)';
            if (level == 'MS') displayLabel = 'MS (Master of Science)';
            if (level == 'BS+MS') displayLabel = 'BS + MS (Combined Program)';
            
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

  /// Build graduation date field (month + year dropdowns)
  static Widget buildGraduationDateField(
    BuildContext context,
    String? selectedMonth,
    String? selectedYear,
    Function(String?) onMonthChanged,
    Function(String?) onYearChanged,
  ) {
    final years = FormOptions.getGraduationYears();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Expected graduation date *',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            fontWeight: FontWeight.w600,
          ),
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
                    'Month',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 8),
                  DropdownButtonFormField<String>(
                    initialValue: selectedMonth,
                    decoration: InputDecoration(
                      border: const OutlineInputBorder(),
                      hintText: 'Select',
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
                      filled: true,
                      fillColor: Colors.grey[50],
                    ),
                    items: FormOptions.months.map((month) {
                      return DropdownMenuItem(
                        value: month,
                        child: Text(month),
                      );
                    }).toList(),
                    onChanged: onMonthChanged,
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
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
                      filled: true,
                      fillColor: Colors.grey[50],
                    ),
                    items: years.map((year) {
                      return DropdownMenuItem(
                        value: year,
                        child: Text(year),
                      );
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

  /// Build degree program dropdown (changes based on education level)
  static Widget buildDegreeProgramField(
    BuildContext context,
    String? educationLevel,
    String? selectedProgram,
    Function(String?) onChanged,
  ) {
    final programs = FormOptions.getDegreeProgramsForLevel(educationLevel);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Degree program *',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            fontWeight: FontWeight.w600,
          ),
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
                  : 'Graduate ECE programs and specializations',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).hintColor,
                fontStyle: FontStyle.italic,
              ),
            ),
          ),
        DropdownButtonFormField<String>(
          initialValue: selectedProgram,
          decoration: InputDecoration(
            border: const OutlineInputBorder(),
            hintText: 'Select your degree program',
            filled: true,
            fillColor: Colors.grey[50],
            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
          ),
          items: programs.map((program) {
            return DropdownMenuItem(
              value: program,
              child: Text(program),
            );
          }).toList(),
          onChanged: educationLevel == null ? null : onChanged,
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
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          helperText,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Theme.of(context).hintColor,
          ),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: options.map((option) {
            final isSelected = selectedOptions.contains(option);
            return FilterChip(
              label: Text(option),
              selected: isSelected,
              onSelected: (selected) {
                final newSelection = List<String>.from(selectedOptions);
                if (selected) {
                  newSelection.add(option);
                } else {
                  newSelection.remove(option);
                }
                onChanged(newSelection);
              },
            );
          }).toList(),
        ),
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
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            fontWeight: FontWeight.w600,
          ),
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
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: InkWell(
                onTap: () => onChanged(true),
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
                  decoration: BoxDecoration(
                    border: Border.all(
                      color: selectedValue == true
                          ? Theme.of(context).colorScheme.primary
                          : Colors.grey.shade300,
                      width: selectedValue == true ? 2 : 1,
                    ),
                    borderRadius: BorderRadius.circular(8),
                    color: selectedValue == true
                        ? Theme.of(context).colorScheme.primaryContainer.withValues(alpha: 0.3)
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
                  padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
                  decoration: BoxDecoration(
                    border: Border.all(
                      color: selectedValue == false
                          ? Theme.of(context).colorScheme.primary
                          : Colors.grey.shade300,
                      width: selectedValue == false ? 2 : 1,
                    ),
                    borderRadius: BorderRadius.circular(8),
                    color: selectedValue == false
                        ? Theme.of(context).colorScheme.primaryContainer.withValues(alpha: 0.3)
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
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          'Select all that you are involved with',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Theme.of(context).hintColor,
          ),
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
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 8),
              TextButton.icon(
                onPressed: () => _showOrgsDialog(context, selectedOrgs, onChanged),
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
    showDialog(
      context: context,
      builder: (context) {
        List<String> tempSelected = List.from(currentSelection);
        String searchQuery = '';
        
        return StatefulBuilder(
          builder: (context, setDialogState) {
            final filteredOrgs = FormOptions.ncsuOrgs
                .where((org) => org.toLowerCase().contains(searchQuery.toLowerCase()))
                .toList();
            
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
                        setDialogState(() => searchQuery = value);
                      },
                    ),
                    const SizedBox(height: 16),
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
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          maxLines: 5,
          decoration: const InputDecoration(
            hintText: 'Share your story, interests, goals, or anything else you\'d like your mentor to know...',
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
        color: Theme.of(context).colorScheme.primaryContainer.withValues(alpha: 0.3),
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
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '1 = Not important | 2 = Slightly important | 3 = Important | 4 = Very important',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Theme.of(context).hintColor,
            ),
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
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.w500,
          ),
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
}

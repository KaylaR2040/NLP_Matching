import 'package:flutter/material.dart';
import '../constants/form_options.dart';

/// Reusable UI builders for the mentor interest form.
class FormFieldWidgets {
  /// Section title with bottom divider.
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

  /// Email field.
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
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          keyboardType: TextInputType.emailAddress,
          decoration: const InputDecoration(
            hintText: 'name@email.com',
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
          runSpacing: 8,
          children: FormOptions.pronouns.map((p) {
            final selected = selectedPronoun == p;
            return ChoiceChip(
              label: Text(p),
              selected: selected,
              onSelected: (_) => onChanged(p),
            );
          }).toList(),
        ),
      ],
    );
  }

  /// Education level selector.
  static Widget buildEducationLevelField(
    BuildContext context,
    String? selected,
    Function(String?) onChanged,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Education level *',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                fontWeight: FontWeight.w600,
              ),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: FormOptions.educationLevels.map((level) {
            return ChoiceChip(
              label: Text(level),
              selected: selected == level,
              onSelected: (_) => onChanged(level),
            );
          }).toList(),
        ),
      ],
    );
  }

  /// Graduation date (semester + year) dropdowns.
  static Widget buildGraduationDateField(
    BuildContext context,
    String? semester,
    String? year,
    Function(String?) onSemesterChanged,
    Function(String?) onYearChanged,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Graduation date',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                fontWeight: FontWeight.w600,
              ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: DropdownButtonFormField<String>(
                value: semester,
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  hintText: 'Semester',
                ),
                items: FormOptions.semester
                    .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                    .toList(),
                onChanged: onSemesterChanged,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: DropdownButtonFormField<String>(
                value: year,
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  hintText: 'Year',
                ),
                items: FormOptions.getGraduationYears()
                    .map((y) => DropdownMenuItem(value: y, child: Text(y)))
                    .toList(),
                onChanged: onYearChanged,
              ),
            ),
          ],
        ),
      ],
    );
  }

  /// Degree program multi-select with search.
  static Widget buildDegreeProgramField(
    BuildContext context,
    List<String> degreeLevels,
    List<String> selected,
    Function(List<String>) onChanged,
  ) {
    final options = FormOptions.getDegreeProgramsForLevels(degreeLevels);
    if (options.isEmpty) {
      return const SizedBox.shrink();
    }
    return _buildSearchableMultiSelect(
      context,
      'Degree program(s) *',
      'Search programs...',
      options,
      selected,
      onChanged,
    );
  }

  /// Organizations multi-select with search.
  static Widget buildOrganizationsField(
    BuildContext context,
    List<String> selected,
    Function(List<String>) onChanged,
  ) {
    return _buildSearchableMultiSelect(
      context,
      'Student organizations you are/were involved with',
      'Search organizations...',
      FormOptions.ncsuOrgs,
      selected,
      onChanged,
    );
  }

  /// Yes / No toggle.
  static Widget buildYesNoField(
    BuildContext context,
    String label,
    bool? value,
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
            ChoiceChip(
              label: const Text('Yes'),
              selected: value == true,
              onSelected: (_) => onChanged(true),
            ),
            const SizedBox(width: 8),
            ChoiceChip(
              label: const Text('No'),
              selected: value == false,
              onSelected: (_) => onChanged(false),
            ),
          ],
        ),
      ],
    );
  }

  /// Single-select chip row.
  static Widget buildSingleSelectChips(
    BuildContext context,
    String label,
    String? subtitle,
    List<String> options,
    String? selected,
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
        if (subtitle != null) ...[
          const SizedBox(height: 4),
          Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
        ],
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: options.map((opt) {
            return ChoiceChip(
              label: Text(opt),
              selected: selected == opt,
              onSelected: (_) => onChanged(opt),
            );
          }).toList(),
        ),
      ],
    );
  }

  /// Multi-select chip row.
  static Widget buildMultiSelectChips(
    BuildContext context,
    String label,
    String? subtitle,
    List<String> options,
    List<String> selected,
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
        if (subtitle != null) ...[
          const SizedBox(height: 4),
          Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
        ],
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: options.map((opt) {
            final isSelected = selected.contains(opt);
            return FilterChip(
              label: Text(opt),
              selected: isSelected,
              onSelected: (_) {
                final updated = List<String>.from(selected);
                if (isSelected) {
                  updated.remove(opt);
                } else {
                  updated.add(opt);
                }
                onChanged(updated);
              },
            );
          }).toList(),
        ),
      ],
    );
  }

  /// Multi-line text field.
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
          maxLines: 4,
          decoration: const InputDecoration(
            border: OutlineInputBorder(),
            hintText: 'Type here...',
          ),
        ),
      ],
    );
  }

  /// Slider for max mentees.
  static Widget buildMaxMenteesSlider(
    BuildContext context,
    int value,
    Function(int) onChanged,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Maximum number of mentees you can take *',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                fontWeight: FontWeight.w600,
              ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: Slider(
                value: value.toDouble(),
                min: 1,
                max: 5,
                divisions: 4,
                label: value.toString(),
                onChanged: (v) => onChanged(v.round()),
              ),
            ),
            Text(
              '$value',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
          ],
        ),
      ],
    );
  }

  // ── Private helpers ──────────────────────────────────────────────

  static Widget _buildSearchableMultiSelect(
    BuildContext context,
    String label,
    String searchHint,
    List<String> options,
    List<String> selected,
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
        const SizedBox(height: 8),
        // Show selected items as chips
        if (selected.isNotEmpty)
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: selected.map((item) {
              return Chip(
                label: Text(item, style: const TextStyle(fontSize: 12)),
                deleteIcon: const Icon(Icons.close, size: 16),
                onDeleted: () {
                  final updated = List<String>.from(selected)..remove(item);
                  onChanged(updated);
                },
              );
            }).toList(),
          ),
        const SizedBox(height: 8),
        // Add button opens dialog
        OutlinedButton.icon(
          onPressed: () => _showSearchDialog(
            context,
            label,
            searchHint,
            options,
            selected,
            onChanged,
          ),
          icon: const Icon(Icons.add),
          label: const Text('Add'),
        ),
      ],
    );
  }

  static void _showSearchDialog(
    BuildContext context,
    String title,
    String searchHint,
    List<String> options,
    List<String> selected,
    Function(List<String>) onChanged,
  ) {
    String query = '';
    final tempSelected = List<String>.from(selected);

    showDialog(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            final filtered = options
                .where((o) => o.toLowerCase().contains(query.toLowerCase()))
                .toList();

            return AlertDialog(
              title: Text(title),
              content: SizedBox(
                width: double.maxFinite,
                height: 400,
                child: Column(
                  children: [
                    TextField(
                      decoration: InputDecoration(
                        hintText: searchHint,
                        prefixIcon: const Icon(Icons.search),
                        border: const OutlineInputBorder(),
                      ),
                      onChanged: (v) => setDialogState(() => query = v),
                    ),
                    const SizedBox(height: 8),
                    Expanded(
                      child: ListView.builder(
                        itemCount: filtered.length,
                        itemBuilder: (context, index) {
                          final item = filtered[index];
                          final checked = tempSelected.contains(item);
                          return CheckboxListTile(
                            title: Text(item, style: const TextStyle(fontSize: 14)),
                            value: checked,
                            dense: true,
                            onChanged: (_) {
                              setDialogState(() {
                                if (checked) {
                                  tempSelected.remove(item);
                                } else {
                                  tempSelected.add(item);
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
                FilledButton(
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
}

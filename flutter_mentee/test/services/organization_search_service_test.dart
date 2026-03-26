import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:flutter_userforms/services/organization_alias_index.dart';
import 'package:flutter_userforms/services/organization_search_service.dart';

void main() {
  group('OrganizationAliasIndex', () {
    test('builds acronyms from significant words in local names', () {
      final index = OrganizationAliasIndex();

      index.preloadNames(const [
        'Institute of Electrical and Electronics Engineers',
        'The Society of Women Engineers',
      ]);

      expect(
        index.lookup('ieee'),
        contains('Institute of Electrical and Electronics Engineers'),
      );
      expect(index.lookup('swe'), contains('The Society of Women Engineers'));
    });

    test('learns slug aliases from organization links', () async {
      final service = OrganizationSearchService(
        client: MockClient((request) async {
          return http.Response(
            jsonEncode({
              'data': {
                'getSearchOrganizations': [
                  {
                    'primaryText':
                        'Institute of Electrical and Electronics Engineers',
                    'link': '/organization/ieee',
                  },
                ],
              },
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }),
      );

      await service.search('robotics', const []);

      expect(
        service.aliasMapSnapshot['ieee'],
        contains('Institute of Electrical and Electronics Engineers'),
      );
    });
  });

  group('OrganizationSearchService', () {
    test(
      'merges alias, local, and remote results without duplicates',
      () async {
        final service = OrganizationSearchService(
          client: MockClient((request) async {
            return http.Response(
              jsonEncode({
                'data': {
                  'getSearchOrganizations': [
                    {
                      'primaryText':
                          'Institute of Electrical and Electronics Engineers',
                      'link': '/organization/ieee',
                    },
                    {
                      'primaryText': 'IEEE Robotics and Automation Society',
                      'link': '/organization/ieee-ras',
                    },
                  ],
                },
              }),
              200,
              headers: {'content-type': 'application/json'},
            );
          }),
        );

        final firstResults = await service.search('robotics', const [
          'Robotics Club',
          'Institute of Electrical and Electronics Engineers',
        ]);

        expect(firstResults, contains('Robotics Club'));
        expect(
          firstResults,
          contains('Institute of Electrical and Electronics Engineers'),
        );
        expect(firstResults, contains('IEEE Robotics and Automation Society'));

        final secondResults = await service.search('ieee', const [
          'Robotics Club',
        ]);

        expect(
          secondResults.first,
          'Institute of Electrical and Electronics Engineers',
        );
        expect(secondResults, contains('IEEE Robotics and Automation Society'));
        expect(
          secondResults
              .where(
                (result) =>
                    result ==
                    'Institute of Electrical and Electronics Engineers',
              )
              .length,
          1,
        );
      },
    );
  });
}

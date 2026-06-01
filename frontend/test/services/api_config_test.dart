import 'package:bloom_scroll/services/api_config.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('uses the local API base when no dart define is supplied', () {
    expect(ApiConfig.baseUrl, 'http://localhost:8000');
    expect(ApiConfig.apiUrl, 'http://localhost:8000/api/v1');
  });
}

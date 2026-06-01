import 'package:bloom_scroll/services/storage_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('initializes daily read state for the current date', () async {
    final service = StorageService();

    await service.init();

    final today = DateTime.now().toIso8601String().split('T').first;
    expect(await service.getReadCount(), 0);
    expect(await service.getReadCardIds(), isEmpty);
    expect(service.lastResetDate, today);
  });

  test('markCardAsRead increments only for new cards', () async {
    final service = StorageService();
    await service.init();

    await service.markCardAsRead('card-1');
    await service.markCardAsRead('card-1');
    await service.markCardAsRead('card-2');

    expect(await service.getReadCount(), 2);
    expect(await service.getReadCardIds(), ['card-1', 'card-2']);
    expect(await service.isCardRead('card-1'), isTrue);
    expect(await service.isCardRead('card-3'), isFalse);
  });

  test('resets stale read state on a new day', () async {
    SharedPreferences.setMockInitialValues({
      'bloom_read_count': 7,
      'bloom_last_reset_date': '2000-01-01',
      'bloom_read_card_ids': ['old-card'],
    });

    final service = StorageService();
    await service.init();

    final today = DateTime.now().toIso8601String().split('T').first;
    expect(await service.getReadCount(), 0);
    expect(await service.getReadCardIds(), isEmpty);
    expect(service.lastResetDate, today);
  });
}

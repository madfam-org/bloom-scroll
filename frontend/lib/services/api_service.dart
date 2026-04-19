/// API service for communicating with Bloom Scroll backend
library;

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import '../models/bloom_card.dart';
import 'api_config.dart';

/// Retry interceptor with exponential backoff
class RetryInterceptor extends Interceptor {
  final Dio dio;
  final int maxRetries;

  RetryInterceptor({
    required this.dio,
    this.maxRetries = 3,
  });

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    // Only retry on network errors or timeouts
    if (err.type == DioExceptionType.connectionTimeout ||
        err.type == DioExceptionType.receiveTimeout ||
        err.type == DioExceptionType.sendTimeout ||
        err.type == DioExceptionType.connectionError) {

      final retryCount = err.requestOptions.extra['retry_count'] as int? ?? 0;

      if (retryCount < maxRetries) {
        // Exponential backoff: 1s, 2s, 4s
        final delaySeconds = (1 << retryCount);
        debugPrint('🔄 Retry attempt ${retryCount + 1}/$maxRetries after ${delaySeconds}s...');

        await Future.delayed(Duration(seconds: delaySeconds));

        // Increment retry count
        err.requestOptions.extra['retry_count'] = retryCount + 1;

        try {
          // Retry the request
          final response = await dio.fetch(err.requestOptions);
          return handler.resolve(response);
        } catch (e) {
          // If retry fails, continue to next retry or fail
          if (e is DioException) {
            return onError(e, handler);
          }
        }
      }
    }

    // If max retries reached or non-retryable error, pass to handler
    super.onError(err, handler);
  }
}

class ApiService {
  late final Dio _dio;

  ApiService() {
    _dio = Dio(
      BaseOptions(
        baseUrl: ApiConfig.apiUrl,
        connectTimeout: ApiConfig.timeout,
        receiveTimeout: ApiConfig.timeout,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    // Add retry interceptor (must be first to catch errors)
    _dio.interceptors.add(RetryInterceptor(dio: _dio, maxRetries: 3));

    // Add logging (after retry to see final result)
    if (ApiConfig.enableLogging && kDebugMode) {
      _dio.interceptors.add(
        LogInterceptor(
          requestBody: true,
          responseBody: true,
          error: true,
          logPrint: (obj) => debugPrint(obj.toString()),
        ),
      );
    }
  }

  /// Fetch the bloom feed with pagination (STORY-007)
  Future<FeedResponse> getFeed({
    int page = 1,
    int readCount = 0,
    int limit = 10,
    List<String>? userContext,
  }) async {
    try {
      // Explicit Map<String, dynamic> so that adding List<String>
      // user_context below doesn't clash with the inferred int-only type
      // from the literal integer fields.
      final Map<String, dynamic> queryParams = <String, dynamic>{
        'page': page,
        'read_count': readCount,
        'limit': limit,
      };

      // Add user context if provided (for serendipity scoring)
      if (userContext != null && userContext.isNotEmpty) {
        queryParams['user_context'] = userContext;
      }

      final response = await _dio.get(
        '/feed',
        queryParameters: queryParams,
      );
      return FeedResponse.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      debugPrint('❌ Error fetching feed: ${e.message}');
      debugPrint('   Type: ${e.type}');
      debugPrint('   Status: ${e.response?.statusCode}');

      // Provide user-friendly error messages
      String userMessage;
      switch (e.type) {
        case DioExceptionType.connectionTimeout:
        case DioExceptionType.sendTimeout:
        case DioExceptionType.receiveTimeout:
          userMessage = 'Request timed out. Please check your connection.';
          break;
        case DioExceptionType.connectionError:
          userMessage = 'Cannot connect to server. Please check your network.';
          break;
        case DioExceptionType.badResponse:
          userMessage = 'Server error (${e.response?.statusCode}). Please try again.';
          break;
        default:
          userMessage = 'Failed to load feed. Please try again.';
      }

      throw Exception(userMessage);
    } catch (e) {
      debugPrint('❌ Unexpected error: $e');
      throw Exception('An unexpected error occurred. Please try again.');
    }
  }

  /// Ingest a single OWID dataset (for testing)
  Future<BloomCard> ingestOwid({
    String datasetKey = 'co2_emissions',
    String entity = 'World',
    int yearsBack = 20,
  }) async {
    try {
      final response = await _dio.post(
        '/ingest/owid',
        queryParameters: {
          'dataset_key': datasetKey,
          'entity': entity,
          'years_back': yearsBack,
        },
      );
      return BloomCard.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      debugPrint('Error ingesting OWID data: ${e.message}');
      rethrow;
    }
  }

  /// Get list of available datasets
  Future<Map<String, dynamic>> getAvailableDatasets() async {
    try {
      final response = await _dio.get('/ingest/datasets');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      debugPrint('Error fetching datasets: ${e.message}');
      rethrow;
    }
  }

  /// Check backend health
  Future<bool> checkHealth() async {
    try {
      final response = await _dio.get('$baseUrl/health');
      return response.statusCode == 200;
    } on DioException catch (e) {
      debugPrint('Health check failed: ${e.message}');
      return false;
    }
  }

  String get baseUrl => ApiConfig.baseUrl;
}

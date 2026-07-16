// k6 load test for the feed hot path (2026-07-16 plan, Phase 4).
//
// Usage:
//   k6 run scripts/load-test.k6.js                        # local (compose stack)
//   k6 run -e API_URL=https://api.almanac.solar scripts/load-test.k6.js
//
// Stays under the app-level rate limit (120/min/IP) by default; raise VUS
// only against local/staging stacks. Thresholds encode the SLO the plan's
// load/soak item calls for: p95 < 500ms, error rate < 1%.
import http from 'k6/http';
import { check, sleep } from 'k6';

const API_URL = __ENV.API_URL || 'http://localhost:8000';

export const options = {
  scenarios: {
    feed_browse: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: '30s', target: 10 },
        { duration: '2m', target: 10 },
        { duration: '30s', target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const health = http.get(`${API_URL}/health`);
  check(health, { 'health 200': (r) => r.status === 200 });

  const feed = http.get(`${API_URL}/api/v1/feed?limit=10`);
  check(feed, {
    'feed 200': (r) => r.status === 200,
    'feed has cards field': (r) => r.json('cards') !== undefined,
    'feed pagination honest': (r) => r.json('pagination.daily_limit') === 20,
  });

  sleep(1);
}

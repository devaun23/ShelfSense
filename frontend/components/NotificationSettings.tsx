'use client';

import { useState, useEffect } from 'react';
import { Bell, BellOff, Clock, Smartphone, CheckCircle } from 'lucide-react';

interface NotificationPreferences {
  push_enabled: boolean;
  daily_reminder: boolean;
  reminder_time: string | null;
  streak_alerts: boolean;
  achievement_alerts: boolean;
}

export default function NotificationSettings() {
  const [preferences, setPreferences] = useState<NotificationPreferences>({
    push_enabled: false,
    daily_reminder: false,
    reminder_time: '09:00',
    streak_alerts: true,
    achievement_alerts: true
  });
  const [permission, setPermission] = useState<NotificationPermission>('default');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testSent, setTestSent] = useState(false);

  useEffect(() => {
    // Check notification permission
    if ('Notification' in window) {
      setPermission(Notification.permission);
    }
    fetchPreferences();
  }, []);

  async function fetchPreferences() {
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/notifications/preferences`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });

      if (res.ok) {
        const data = await res.json();
        setPreferences(data);
      }
    } catch (error) {
      console.error('Failed to fetch notification preferences:', error);
    } finally {
      setLoading(false);
    }
  }

  async function requestPermission() {
    if (!('Notification' in window)) {
      alert('Push notifications are not supported in this browser');
      return;
    }

    const result = await Notification.requestPermission();
    setPermission(result);

    if (result === 'granted') {
      await subscribeToPush();
    }
  }

  async function subscribeToPush() {
    try {
      // Register service worker
      const registration = await navigator.serviceWorker.register('/sw.js');
      await navigator.serviceWorker.ready;

      // Get VAPID public key
      const keyRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/notifications/vapid-public-key`);
      if (!keyRes.ok) {
        console.error('Push notifications not configured on server');
        return;
      }
      const { vapid_public_key } = await keyRes.json();

      // Convert VAPID key to Uint8Array
      const applicationServerKey = urlBase64ToUint8Array(vapid_public_key);

      // Subscribe to push
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: applicationServerKey.buffer as ArrayBuffer
      });

      // Send subscription to server
      const token = localStorage.getItem('auth_token');
      const subRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/notifications/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          endpoint: subscription.endpoint,
          keys: {
            p256dh: arrayBufferToBase64(subscription.getKey('p256dh')),
            auth: arrayBufferToBase64(subscription.getKey('auth'))
          },
          device_name: getDeviceName()
        })
      });

      if (subRes.ok) {
        setPreferences(prev => ({ ...prev, push_enabled: true }));
      }
    } catch (error) {
      console.error('Failed to subscribe to push:', error);
    }
  }

  async function savePreferences() {
    setSaving(true);
    try {
      const token = localStorage.getItem('auth_token');
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/notifications/preferences`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify(preferences)
      });
    } catch (error) {
      console.error('Failed to save preferences:', error);
    } finally {
      setSaving(false);
    }
  }

  async function sendTestNotification() {
    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/notifications/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          title: 'Test Notification',
          body: 'Push notifications are working!'
        })
      });

      if (res.ok) {
        setTestSent(true);
        setTimeout(() => setTestSent(false), 3000);
      }
    } catch (error) {
      console.error('Failed to send test notification:', error);
    }
  }

  if (loading) {
    return (
      <div className="animate-pulse bg-zinc-800/50 rounded-lg p-4">
        <div className="h-6 w-48 bg-zinc-700 rounded mb-4" />
        <div className="h-4 w-full bg-zinc-700 rounded" />
      </div>
    );
  }

  return (
    <div className="bg-zinc-800/50 rounded-xl border border-zinc-700/50 p-6">
      <h3 className="text-lg font-semibold text-zinc-100 flex items-center gap-2 mb-4">
        <Bell className="w-5 h-5 text-violet-400" />
        Push Notifications
      </h3>

      {/* Permission Status */}
      {permission === 'denied' && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 mb-4">
          <p className="text-sm text-red-300 flex items-center gap-2">
            <BellOff className="w-4 h-4" />
            Notifications are blocked. Enable them in your browser settings.
          </p>
        </div>
      )}

      {permission === 'default' && (
        <button
          onClick={requestPermission}
          className="w-full bg-violet-600 hover:bg-violet-500 text-white font-medium py-3 px-4 rounded-lg transition-colors mb-4 flex items-center justify-center gap-2"
        >
          <Bell className="w-5 h-5" />
          Enable Push Notifications
        </button>
      )}

      {permission === 'granted' && !preferences.push_enabled && (
        <button
          onClick={subscribeToPush}
          className="w-full bg-violet-600 hover:bg-violet-500 text-white font-medium py-3 px-4 rounded-lg transition-colors mb-4 flex items-center justify-center gap-2"
        >
          <Smartphone className="w-5 h-5" />
          Subscribe This Device
        </button>
      )}

      {preferences.push_enabled && (
        <div className="space-y-4">
          {/* Daily Reminder Toggle */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-zinc-200">Daily Study Reminder</p>
              <p className="text-xs text-zinc-400">Get reminded to study every day</p>
            </div>
            <button
              onClick={() => {
                setPreferences(prev => ({ ...prev, daily_reminder: !prev.daily_reminder }));
              }}
              className={`w-12 h-6 rounded-full transition-colors ${
                preferences.daily_reminder ? 'bg-violet-600' : 'bg-zinc-700'
              }`}
            >
              <div className={`w-5 h-5 rounded-full bg-white shadow transition-transform ${
                preferences.daily_reminder ? 'translate-x-6' : 'translate-x-0.5'
              }`} />
            </button>
          </div>

          {/* Reminder Time */}
          {preferences.daily_reminder && (
            <div className="flex items-center gap-3">
              <Clock className="w-4 h-4 text-zinc-400" />
              <select
                value={preferences.reminder_time || '09:00'}
                onChange={(e) => setPreferences(prev => ({ ...prev, reminder_time: e.target.value }))}
                className="bg-zinc-700 border border-zinc-600 rounded-lg px-3 py-2 text-sm text-zinc-200"
              >
                {Array.from({ length: 24 }, (_, i) => {
                  const hour = i.toString().padStart(2, '0');
                  return (
                    <option key={hour} value={`${hour}:00`}>
                      {i === 0 ? '12:00 AM' : i < 12 ? `${i}:00 AM` : i === 12 ? '12:00 PM' : `${i - 12}:00 PM`}
                    </option>
                  );
                })}
              </select>
              <span className="text-xs text-zinc-500">(UTC)</span>
            </div>
          )}

          {/* Streak Alerts */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-zinc-200">Streak Alerts</p>
              <p className="text-xs text-zinc-400">Warn when your streak is at risk</p>
            </div>
            <button
              onClick={() => setPreferences(prev => ({ ...prev, streak_alerts: !prev.streak_alerts }))}
              className={`w-12 h-6 rounded-full transition-colors ${
                preferences.streak_alerts ? 'bg-violet-600' : 'bg-zinc-700'
              }`}
            >
              <div className={`w-5 h-5 rounded-full bg-white shadow transition-transform ${
                preferences.streak_alerts ? 'translate-x-6' : 'translate-x-0.5'
              }`} />
            </button>
          </div>

          {/* Save Button */}
          <button
            onClick={savePreferences}
            disabled={saving}
            className="w-full bg-zinc-700 hover:bg-zinc-600 text-white font-medium py-2 px-4 rounded-lg transition-colors"
          >
            {saving ? 'Saving...' : 'Save Preferences'}
          </button>

          {/* Test Notification */}
          <button
            onClick={sendTestNotification}
            className="w-full bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-sm py-2 px-4 rounded-lg transition-colors border border-zinc-700 flex items-center justify-center gap-2"
          >
            {testSent ? (
              <>
                <CheckCircle className="w-4 h-4 text-emerald-400" />
                Sent!
              </>
            ) : (
              'Send Test Notification'
            )}
          </button>
        </div>
      )}
    </div>
  );
}

// Helper functions
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

function arrayBufferToBase64(buffer: ArrayBuffer | null): string {
  if (!buffer) return '';
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}

function getDeviceName(): string {
  const ua = navigator.userAgent;
  if (ua.includes('Chrome')) return 'Chrome';
  if (ua.includes('Firefox')) return 'Firefox';
  if (ua.includes('Safari')) return 'Safari';
  if (ua.includes('Edge')) return 'Edge';
  return 'Unknown Browser';
}

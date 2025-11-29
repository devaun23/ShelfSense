'use client';

import { useState, useEffect, use, useCallback } from 'react';
import { useUser } from '@/contexts/UserContext';
import { getSpecialtyBySlug } from '@/lib/specialties';
import PortalSidebar from '@/components/PortalSidebar';

interface StudySyncProps {
  params: Promise<{ specialty: string }>;
}

interface Upload {
  id: string;
  filename: string;
  file_type: string;
  status: string;
  context: string;
  course_name: string;
  topics_found: number;
  uploaded_at: string;
}

interface TopicStat {
  topic: string;
  specialty: string | null;
  questions_available: number;
  completed: number;
  accuracy: number;
  mastery: string;
  is_high_yield: boolean;
}

interface StudyFocus {
  has_focus: boolean;
  focus_specialty: string | null;
  focus_topics: string[];
  weak_areas: string[];
  daily_target: number;
  topic_stats: TopicStat[];
  message?: string;
}

export default function StudySyncPage({ params }: StudySyncProps) {
  const { user, isLoading: userLoading, getAccessToken } = useUser();
  const resolvedParams = use(params);
  const specialty = getSpecialtyBySlug(resolvedParams.specialty);

  const [uploads, setUploads] = useState<Upload[]>([]);
  const [studyFocus, setStudyFocus] = useState<StudyFocus | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [isLoadingData, setIsLoadingData] = useState(true);

  // File upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadContext, setUploadContext] = useState<string>('lecture');
  const [courseName, setCourseName] = useState<string>('');

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchData = useCallback(async () => {
    if (!user) return;

    try {
      const token = await getAccessToken();

      // Fetch uploads and study focus in parallel
      const [uploadsRes, focusRes] = await Promise.all([
        fetch(`${API_URL}/api/curriculum/uploads`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        fetch(`${API_URL}/api/curriculum/focus`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);

      if (uploadsRes.ok) {
        const data = await uploadsRes.json();
        setUploads(data.uploads || []);
      }

      if (focusRes.ok) {
        const data = await focusRes.json();
        setStudyFocus(data);
      }
    } catch (error) {
      console.error('Failed to fetch curriculum data:', error);
    } finally {
      setIsLoadingData(false);
    }
  }, [user, getAccessToken, API_URL]);

  useEffect(() => {
    if (user) {
      fetchData();
    }
  }, [user, fetchData]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file size (10MB max)
      if (file.size > 10 * 1024 * 1024) {
        setUploadError('File too large. Maximum size is 10MB.');
        return;
      }
      setSelectedFile(file);
      setUploadError(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !user) return;

    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const token = await getAccessToken();
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('context', uploadContext);
      if (courseName) {
        formData.append('course_name', courseName);
      }

      const response = await fetch(`${API_URL}/api/curriculum/upload`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`
        },
        body: formData
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Upload failed');
      }

      setUploadSuccess(data.message);
      setSelectedFile(null);
      setCourseName('');

      // Refresh data
      await fetchData();

    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  if (userLoading || !specialty) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#4169E1]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black flex">
      <PortalSidebar specialty={specialty} />

      <main className="flex-1 ml-64 p-8">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-2xl font-serif text-white mb-2">StudySync AI</h1>
            <p className="text-gray-400">
              Upload lecture slides, PDFs, or NBME score reports to personalize your study sessions.
            </p>
          </div>

          {/* Upload Section */}
          <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6 mb-8">
            <h2 className="text-lg font-medium text-white mb-4">Upload Content</h2>

            {/* Upload Context Selection */}
            <div className="mb-4">
              <label className="block text-sm text-gray-400 mb-2">What are you uploading?</label>
              <div className="flex gap-3">
                {[
                  { value: 'lecture', label: 'Lecture Slides' },
                  { value: 'nbme_report', label: 'NBME Report' },
                  { value: 'syllabus', label: 'Syllabus' },
                  { value: 'notes', label: 'Notes' }
                ].map((option) => (
                  <button
                    key={option.value}
                    onClick={() => setUploadContext(option.value)}
                    className={`px-4 py-2 rounded-lg text-sm transition-colors ${
                      uploadContext === option.value
                        ? 'bg-[#4169E1] text-white'
                        : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Course Name (optional) */}
            {uploadContext !== 'nbme_report' && (
              <div className="mb-4">
                <label className="block text-sm text-gray-400 mb-2">Course/Rotation Name (optional)</label>
                <input
                  type="text"
                  value={courseName}
                  onChange={(e) => setCourseName(e.target.value)}
                  placeholder="e.g., Internal Medicine Clerkship"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-[#4169E1]"
                />
              </div>
            )}

            {/* File Selection */}
            <div className="mb-4">
              <label className="block text-sm text-gray-400 mb-2">Select File</label>
              <div className="flex items-center gap-4">
                <label className="flex-1 cursor-pointer">
                  <div className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                    selectedFile ? 'border-[#4169E1] bg-[#4169E1]/10' : 'border-gray-700 hover:border-gray-600'
                  }`}>
                    {selectedFile ? (
                      <div className="flex items-center justify-center gap-2 text-white">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                          <polyline points="14 2 14 8 20 8" />
                        </svg>
                        <span>{selectedFile.name}</span>
                        <span className="text-gray-400 text-sm">
                          ({(selectedFile.size / 1024 / 1024).toFixed(1)} MB)
                        </span>
                      </div>
                    ) : (
                      <div className="text-gray-400">
                        <svg className="mx-auto mb-2" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                          <polyline points="17 8 12 3 7 8" />
                          <line x1="12" y1="3" x2="12" y2="15" />
                        </svg>
                        <p>Click to select PDF, PPTX, or image</p>
                        <p className="text-xs mt-1">Max 10MB</p>
                      </div>
                    )}
                  </div>
                  <input
                    type="file"
                    onChange={handleFileSelect}
                    accept=".pdf,.pptx,.ppt,.docx,.doc,.png,.jpg,.jpeg"
                    className="hidden"
                  />
                </label>
              </div>
            </div>

            {/* Upload Button */}
            <button
              onClick={handleUpload}
              disabled={!selectedFile || isUploading}
              className={`w-full py-3 rounded-lg font-medium transition-colors ${
                selectedFile && !isUploading
                  ? 'bg-[#4169E1] text-white hover:bg-[#3457b1]'
                  : 'bg-gray-800 text-gray-500 cursor-not-allowed'
              }`}
            >
              {isUploading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Analyzing with AI...
                </span>
              ) : (
                'Upload & Analyze'
              )}
            </button>

            {/* Status Messages */}
            {uploadError && (
              <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
                {uploadError}
              </div>
            )}
            {uploadSuccess && (
              <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-400 text-sm">
                {uploadSuccess}
              </div>
            )}
          </div>

          {/* Study Focus Summary */}
          {studyFocus?.has_focus && (
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6 mb-8">
              <h2 className="text-lg font-medium text-white mb-4">Your Study Focus</h2>

              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-gray-800/50 rounded-lg p-4">
                  <p className="text-gray-400 text-sm mb-1">Primary Specialty</p>
                  <p className="text-white font-medium">{studyFocus.focus_specialty || 'Not set'}</p>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-4">
                  <p className="text-gray-400 text-sm mb-1">Daily Target</p>
                  <p className="text-white font-medium">{studyFocus.daily_target} questions</p>
                </div>
              </div>

              {/* Weak Areas */}
              {studyFocus.weak_areas.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-sm font-medium text-gray-400 mb-2">Weak Areas (from NBME)</h3>
                  <div className="flex flex-wrap gap-2">
                    {studyFocus.weak_areas.map((area, i) => (
                      <span key={i} className="px-3 py-1 bg-red-500/20 text-red-400 rounded-full text-sm">
                        {area}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Focus Topics */}
              {studyFocus.focus_topics.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-400 mb-2">Focus Topics</h3>
                  <div className="flex flex-wrap gap-2">
                    {studyFocus.focus_topics.slice(0, 10).map((topic, i) => (
                      <span key={i} className="px-3 py-1 bg-[#4169E1]/20 text-[#4169E1] rounded-full text-sm">
                        {topic}
                      </span>
                    ))}
                    {studyFocus.focus_topics.length > 10 && (
                      <span className="px-3 py-1 bg-gray-800 text-gray-400 rounded-full text-sm">
                        +{studyFocus.focus_topics.length - 10} more
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Topic Progress */}
              {studyFocus.topic_stats.length > 0 && (
                <div className="mt-6">
                  <h3 className="text-sm font-medium text-gray-400 mb-3">Topic Progress</h3>
                  <div className="space-y-2">
                    {studyFocus.topic_stats.slice(0, 5).map((stat, i) => (
                      <div key={i} className="flex items-center justify-between bg-gray-800/50 rounded-lg p-3">
                        <div className="flex items-center gap-2">
                          {stat.is_high_yield && (
                            <span className="text-amber-400" title="High Yield">
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                              </svg>
                            </span>
                          )}
                          <span className="text-white text-sm">{stat.topic}</span>
                        </div>
                        <div className="flex items-center gap-4 text-sm">
                          <span className="text-gray-400">{stat.completed}/{stat.questions_available}</span>
                          <span className={stat.accuracy >= 70 ? 'text-emerald-400' : stat.accuracy >= 50 ? 'text-amber-400' : 'text-red-400'}>
                            {stat.accuracy.toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* No Focus State */}
          {studyFocus && !studyFocus.has_focus && (
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-8 text-center">
              <svg className="mx-auto mb-4 text-gray-600" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
              <p className="text-gray-400 mb-2">{studyFocus.message || 'No study focus set yet'}</p>
              <p className="text-sm text-gray-500">
                Upload your lecture slides or an NBME score report to get personalized question recommendations.
              </p>
            </div>
          )}

          {/* Recent Uploads */}
          {uploads.length > 0 && (
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6">
              <h2 className="text-lg font-medium text-white mb-4">Recent Uploads</h2>
              <div className="space-y-3">
                {uploads.map((upload) => (
                  <div key={upload.id} className="flex items-center justify-between bg-gray-800/50 rounded-lg p-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                        upload.context === 'nbme_report' ? 'bg-red-500/20' : 'bg-[#4169E1]/20'
                      }`}>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                          stroke={upload.context === 'nbme_report' ? '#ef4444' : '#4169E1'} strokeWidth="2">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                          <polyline points="14 2 14 8 20 8" />
                        </svg>
                      </div>
                      <div>
                        <p className="text-white text-sm font-medium">{upload.filename}</p>
                        <p className="text-gray-500 text-xs">
                          {upload.course_name || upload.context} - {upload.topics_found} topics found
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        upload.status === 'completed'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : upload.status === 'failed'
                          ? 'bg-red-500/20 text-red-400'
                          : 'bg-amber-500/20 text-amber-400'
                      }`}>
                        {upload.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Loading State */}
          {isLoadingData && (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#4169E1]" />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

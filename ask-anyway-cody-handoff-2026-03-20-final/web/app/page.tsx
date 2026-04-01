export default function Home() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-white">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900">Ask Anyway</h1>
        <p className="mt-4 text-gray-600">Mental health check-in quiz — launching soon.</p>
        <a
          href="/quiz"
          className="mt-6 inline-block px-6 py-3 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-700 transition"
        >
          Take the Quiz
        </a>
      </div>
    </main>
  );
}

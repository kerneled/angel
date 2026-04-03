export default function OfflinePage() {
  return (
    <div className="flex items-center justify-center h-dvh bg-[#1a1a2e] text-gray-100">
      <div className="text-center p-8">
        <p className="text-4xl mb-4">&#128054;</p>
        <h1 className="text-xl font-bold mb-2">Sem conexão</h1>
        <p className="text-gray-400">Aguardando rede...</p>
      </div>
    </div>
  );
}

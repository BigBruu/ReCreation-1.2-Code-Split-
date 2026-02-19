import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../hooks/use-toast';

const LoginPage = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [isAdmin, setIsAdminMode] = useState(false);
  const [formData, setFormData] = useState({ 
    username: '', 
    email: '', 
    password: '', 
    inviteCode: '',
    adminPassword: ''
  });
  const { login, adminLogin, register, loading } = useAuth();
  const { toast } = useToast();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (isAdmin) {
        await adminLogin(formData.adminPassword);
        toast({ title: "Erfolg!", description: "Admin-Login erfolgreich" });
      } else if (isLogin) {
        await login(formData.username, formData.password);
        toast({ title: "Erfolg!", description: "Anmeldung erfolgreich" });
      } else {
        if (!formData.inviteCode.trim()) {
          toast({ title: "Fehler", description: "Einladungscode erforderlich", variant: "destructive" });
          return;
        }
        await register(formData.username, formData.email, formData.password, formData.inviteCode);
        toast({ title: "Erfolg!", description: "Registrierung erfolgreich - Raumhafen wird zugewiesen..." });
      }
      
      setTimeout(() => {
        window.location.href = isAdmin ? '/admin' : '/game';
      }, 1500);
    } catch (error) {
      toast({ title: "Fehler", description: error.message, variant: "destructive" });
    }
  };

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-4 starfield">
      <div className="bg-gray-900 p-8 rounded-lg border border-blue-500 w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-blue-400 mb-2">TheReCreation</h1>
          <p className="text-gray-400">Authentisches Browser-Strategiespiel</p>
          <p className="text-xs text-gray-500 mt-2">47x47 Universum • Einladung erforderlich • Runde 10</p>
        </div>

        <div className="flex space-x-2 mb-6">
          <button
            onClick={() => { setIsAdminMode(false); setIsLogin(true); }}
            className={`flex-1 py-2 px-3 rounded text-sm ${!isAdmin ? 'bg-blue-600' : 'bg-gray-700'}`}
          >
            Spieler
          </button>
          <button
            onClick={() => setIsAdminMode(true)}
            className={`flex-1 py-2 px-3 rounded text-sm ${isAdmin ? 'bg-red-600' : 'bg-gray-700'}`}
          >
            Admin
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {isAdmin ? (
            <div>
              <label className="block text-sm font-medium mb-1">Admin-Passwort</label>
              <input
                type="password"
                value={formData.adminPassword}
                onChange={(e) => setFormData({...formData, adminPassword: e.target.value})}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded focus:border-blue-400 focus:outline-none"
                placeholder="Admin-Passwort eingeben"
                required
              />
            </div>
          ) : (
            <>
              <div>
                <label className="block text-sm font-medium mb-1">Spielername</label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({...formData, username: e.target.value})}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded focus:border-blue-400 focus:outline-none"
                  required
                />
              </div>

              {!isLogin && (
                <div>
                  <label className="block text-sm font-medium mb-1">E-Mail</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded focus:border-blue-400 focus:outline-none"
                    required
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium mb-1">Passwort</label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded focus:border-blue-400 focus:outline-none"
                  required
                />
              </div>

              {!isLogin && (
                <div>
                  <label className="block text-sm font-medium mb-1">Einladungscode *</label>
                  <input
                    type="text"
                    value={formData.inviteCode}
                    onChange={(e) => setFormData({...formData, inviteCode: e.target.value.toUpperCase()})}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded focus:border-blue-400 focus:outline-none"
                    placeholder="8-stelliger Code"
                    maxLength="8"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">Erforderlich für Registrierung</p>
                </div>
              )}
            </>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 py-2 rounded font-medium transition-colors"
          >
            {loading ? 'Lade...' : (isAdmin ? 'Admin-Login' : (isLogin ? 'Anmelden' : 'Registrieren'))}
          </button>
        </form>

        {!isAdmin && (
          <div className="text-center mt-4">
            <button
              onClick={() => setIsLogin(!isLogin)}
              className="text-blue-400 hover:text-blue-300 text-sm"
            >
              {isLogin ? 'Kein Account? Registrieren' : 'Bereits Account? Anmelden'}
            </button>
          </div>
        )}

        <div className="text-center mt-4 text-xs text-gray-500">
          <p>🔒 Geschlossenes Spiel - Nur mit Einladung</p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;

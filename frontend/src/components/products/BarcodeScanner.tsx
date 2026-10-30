'use client';

import { useEffect, useRef, useState } from 'react';
import { BrowserMultiFormatReader } from '@zxing/browser';
import { BarcodeFormat, DecodeHintType } from '@zxing/library';
import { Camera, CameraOff, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';

interface BarcodeScannerProps {
  onDetected: (barcode: string) => void;
  disabled?: boolean;
}

export function BarcodeScanner({ onDetected, disabled = false }: BarcodeScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const readerRef = useRef<BrowserMultiFormatReader | null>(null);
  const controlsRef = useRef<{ stop: () => void } | null>(null);
  const detectedRef = useRef(false);
  const [running, setRunning] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [manualCode, setManualCode] = useState('');

  const stopCamera = () => {
    controlsRef.current?.stop();
    controlsRef.current = null;
    const video = videoRef.current;
    if (video?.srcObject instanceof MediaStream) {
      video.srcObject.getTracks().forEach((track) => track.stop());
      video.srcObject = null;
    }
    setRunning(false);
    setStarting(false);
  };

  const reportCode = (value: string) => {
  let code = value.trim();

  if (code.length === 13 && code.startsWith('0')) {
    code = code.slice(1);
  }

  if (!code || detectedRef.current || disabled) return;
  detectedRef.current = true;
  stopCamera();
  onDetected(code);
};

  const startCamera = async () => {
    if (disabled || running || starting) return;
    setError(null);
    setStarting(true);
    detectedRef.current = false;

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('Este navegador não permite acesso à câmera. Abra o PharmaPredict em um navegador atualizado.');
      }
      if (!videoRef.current) {
        throw new Error('Não foi possível encontrar o elemento de vídeo da câmera.');
      }

      // Prioriza UPC-A de 12 dígitos e formatos EAN, com tentativa de leitura reforçada.
      const hints = new Map();
      hints.set(DecodeHintType.POSSIBLE_FORMATS, [
        BarcodeFormat.UPC_A,
        BarcodeFormat.EAN_13,
        BarcodeFormat.EAN_8,
        BarcodeFormat.CODE_128,
      ]);
      hints.set(DecodeHintType.TRY_HARDER, true);

      const reader = new BrowserMultiFormatReader(hints);
      readerRef.current = reader;
      const controls = await reader.decodeFromVideoDevice(
        undefined,
        videoRef.current,
        (result) => {
          if (result) reportCode(result.getText());
        },
      );
      controlsRef.current = controls;
      const video = videoRef.current;
      if (video) {
        await new Promise<void>((resolve) => {
          if (video.readyState >= 2) return resolve();
          const onReady = () => {
            video.removeEventListener('loadeddata', onReady);
            resolve();
          };
          video.addEventListener('loadeddata', onReady);
          setTimeout(resolve, 2000); // timeout de segurança
        });
        await video.play().catch(() => {});
      }
      setRunning(true);
      setStarting(false);
    } catch (cameraError) {
      stopCamera();
      if (cameraError instanceof DOMException && cameraError.name === 'NotAllowedError') {
        setError('Permita o acesso à câmera nas configurações do navegador.');
      } else if (cameraError instanceof DOMException && cameraError.name === 'NotFoundError') {
        setError('Nenhuma câmera foi encontrada neste notebook.');
      } else {
        setError(cameraError instanceof Error
          ? `Não foi possível iniciar a leitura: ${cameraError.message}`
          : 'Não foi possível iniciar a leitura do código de barras.');
      }
    }
  };

  const handleManualSubmit = () => reportCode(manualCode);

  useEffect(() => {
    return () => {
      controlsRef.current?.stop();
      const video = videoRef.current;
      if (video?.srcObject instanceof MediaStream) {
        video.srcObject.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  return (
    <Card>
      <CardContent className="space-y-4 pt-6">
        <div className="relative aspect-video overflow-hidden rounded-lg bg-black">
          <video ref={videoRef} className="h-full w-full object-cover" style={{ minWidth: 320, minHeight: 240 }} playsInline muted autoPlay/>
          {!running && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-center text-white">
              <Camera className="h-12 w-12 opacity-70" />
              <p className="px-4 text-sm opacity-80">
                Clique em &quot;Abrir câmera&quot; e mantenha o código de barras nítido dentro da imagem.
              </p>
            </div>
          )}
        </div>
        {running && (
          <p className="rounded-md bg-muted p-3 text-sm">
            Leitura ativa. Aproxime o código, mantenha-o na horizontal e evite reflexos. O leitor tenta reconhecer UPC-A de 12 dígitos e EAN.
          </p>
        )}
        {error && <p role="alert" className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}
        <div className="flex flex-wrap gap-2">
          {!running ? (
            <Button onClick={() => void startCamera()} disabled={disabled || starting}>
              {starting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Camera className="mr-2 h-4 w-4" />}
              {starting ? 'Iniciando...' : 'Abrir câmera'}
            </Button>
          ) : (
            <Button variant="outline" onClick={stopCamera}>
              <CameraOff className="mr-2 h-4 w-4" />
              Fechar câmera
            </Button>
          )}
        </div>
        <div className="border-t pt-4">
          <p className="mb-2 text-sm font-medium">Ou digite o código manualmente</p>
          <div className="flex gap-2">
            <Input value={manualCode} onChange={(event) => setManualCode(event.target.value)}
              placeholder="Ex.: 012345678905" inputMode="numeric" disabled={disabled} />
            <Button onClick={handleManualSubmit} disabled={disabled || !manualCode.trim()}>Usar código</Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}


import { useState } from 'react';
import { Mail, MessageSquare, Send, CheckCircle2, ChevronLeft, Building2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useRouter } from '@/lib/router';
import { toast } from 'sonner';

import { sendContactEmail } from '@/lib/api';

export function ContactPage() {
    const router = useRouter();
    const [isSubmitted, setIsSubmitted] = useState(false);
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        subject: '',
        message: ''
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);

        try {
            await sendContactEmail(formData);
            setIsSubmitted(true);
            toast.success('문의가 성공적으로 접수되었습니다.');
        } catch (error) {
            toast.error('문의 접수에 실패했습니다. 잠시 후 다시 시도해주세요.');
        } finally {
            setLoading(false);
        }
    };

    if (isSubmitted) {
        return (
            <div className="container mx-auto px-4 py-20 flex items-center justify-center animate-in fade-in zoom-in duration-500">
                <Card className="max-w-md w-full bg-slate-900/50 border-slate-800 shadow-2xl p-8 text-center space-y-6">
                    <div className="w-20 h-20 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto border border-emerald-500/20">
                        <CheckCircle2 className="w-10 h-10 text-emerald-400" />
                    </div>
                    <div className="space-y-2">
                        <h1 className="text-2xl font-black text-white">문의 접수 완료</h1>
                        <p className="text-slate-400 leading-relaxed">
                            소중한 의견 감사합니다. <br />
                            검토 후 <b>rlaehdrb2485@naver.com</b>으로 <br />
                            빠른 시일 내에 답변 드리겠습니다.
                        </p>
                    </div>
                    <Button
                        variant="outline"
                        onClick={() => router.navigate('/')}
                        className="w-full border-slate-700 hover:bg-slate-800"
                    >
                        홈으로 돌아가기
                    </Button>
                </Card>
            </div>
        );
    }

    return (
        <div className="container mx-auto px-4 py-12 max-w-5xl animate-in fade-in duration-700">
            <Button
                variant="ghost"
                onClick={() => router.navigate('/')}
                className="mb-8 text-slate-500 hover:text-white"
            >
                <ChevronLeft className="w-4 h-4 mr-2" /> 홈으로 돌아가기
            </Button>

            <div className="grid lg:grid-cols-5 gap-12">
                {/* Info Side */}
                <div className="lg:col-span-2 space-y-8">
                    <div className="space-y-4">
                        <Badge variant="outline" className="bg-blue-600/10 text-blue-400 border-blue-500/20 px-3 py-1">
                            Contact Us
                        </Badge>
                        <h1 className="text-4xl font-black text-white leading-tight">
                            도움이 필요하신가요?
                        </h1>
                        <p className="text-slate-400 leading-relaxed">
                            서비스 이용 중 불편한 점이나 제안하고 싶은 기능이 있다면 언제든 말씀해 주세요.
                            사용자 한 분 한 분의 소중한 의견을 경청합니다.
                        </p>
                    </div>

                    <div className="space-y-6">
                        <div className="flex gap-4 items-start p-4 rounded-2xl bg-slate-900/40 border border-slate-800">
                            <div className="p-3 bg-blue-600/10 rounded-xl border border-blue-500/20">
                                <Mail className="w-5 h-5 text-blue-400" />
                            </div>
                            <div>
                                <h4 className="font-bold text-slate-200">Email Address</h4>
                                <p className="text-sm text-slate-500">rlaehdrb2485@naver.com</p>
                            </div>
                        </div>

                        <div className="flex gap-4 items-start p-4 rounded-2xl bg-slate-900/40 border border-slate-800">
                            <div className="p-3 bg-purple-600/10 rounded-xl border border-purple-500/20">
                                <MessageSquare className="w-5 h-5 text-purple-400" />
                            </div>
                            <div>
                                <h4 className="font-bold text-slate-200">고객 지원 시간</h4>
                                <p className="text-sm text-slate-500">평일 09:00 - 18:00 (KST)</p>
                            </div>
                        </div>

                        <div className="flex gap-4 items-start p-4 rounded-2xl bg-slate-900/40 border border-slate-800">
                            <div className="p-3 bg-indigo-600/10 rounded-xl border border-indigo-500/20">
                                <Building2 className="w-5 h-5 text-indigo-400" />
                            </div>
                            <div>
                                <h4 className="font-bold text-slate-200">운영사</h4>
                                <p className="text-sm text-slate-500">CertFinder Lab.</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Form Side */}
                <Card className="lg:col-span-3 bg-slate-900/50 border-slate-800 shadow-2xl rounded-[2.5rem] overflow-hidden">
                    <CardContent className="p-8 md:p-12">
                        <form onSubmit={handleSubmit} className="space-y-6">
                            <div className="grid md:grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <label className="text-sm font-bold text-slate-400 ml-1">성함</label>
                                    <Input
                                        required
                                        placeholder="홍길동"
                                        value={formData.name}
                                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                        className="bg-slate-950 border-slate-800 h-12 focus:ring-blue-500/20"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-sm font-bold text-slate-400 ml-1">이메일</label>
                                    <Input
                                        required
                                        type="email"
                                        placeholder="example@email.com"
                                        value={formData.email}
                                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                        className="bg-slate-950 border-slate-800 h-12 focus:ring-blue-500/20"
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-sm font-bold text-slate-400 ml-1">제목</label>
                                <Input
                                    required
                                    placeholder="문의 제목을 입력해 주세요."
                                    value={formData.subject}
                                    onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                                    className="bg-slate-950 border-slate-800 h-12 focus:ring-blue-500/20"
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="text-sm font-bold text-slate-400 ml-1">상세 내용</label>
                                <textarea
                                    required
                                    placeholder="문의하실 내용을 상세히 적어주세요."
                                    value={formData.message}
                                    onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                                    className="w-full bg-slate-950 border-slate-800 rounded-xl p-4 min-h-[160px] focus:ring-blue-500/20 border outline-none focus:border-blue-500 transition-all text-white placeholder:text-slate-600 shadow-inner"
                                />
                            </div>

                            <Button
                                type="submit"
                                disabled={loading}
                                className="w-full h-14 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-black text-lg rounded-2xl shadow-xl shadow-blue-500/20 transition-all active:scale-[0.98]"
                            >
                                {loading ? (
                                    <div className="flex items-center gap-2">
                                        <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                                        <span>보내는 중...</span>
                                    </div>
                                ) : (
                                    <div className="flex items-center gap-2">
                                        <Send className="w-5 h-5" />
                                        <span>문의 보내기</span>
                                    </div>
                                )}
                            </Button>
                        </form>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}

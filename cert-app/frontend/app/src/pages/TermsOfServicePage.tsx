
import { ChevronLeft, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useRouter } from '@/lib/router';

export function TermsOfServicePage() {
    const router = useRouter();

    return (
        <div className="container mx-auto px-4 py-12 max-w-4xl animate-in fade-in duration-700">
            <Button
                variant="ghost"
                onClick={() => router.navigate('/')}
                className="mb-8 text-slate-500 hover:text-white"
            >
                <ChevronLeft className="w-4 h-4 mr-2" /> 홈으로 돌아가기
            </Button>

            <div className="space-y-10 bg-slate-900/50 border border-slate-800 p-8 md:p-12 rounded-[2.5rem]">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-indigo-600/10 rounded-2xl border border-indigo-500/20">
                        <FileText className="w-8 h-8 text-indigo-400" />
                    </div>
                    <h1 className="text-3xl font-black text-white">이용약관</h1>
                </div>

                <div className="space-y-8 text-slate-300 leading-relaxed">
                    <section className="space-y-4">
                        <h2 className="text-xl font-bold text-white">제 1 조 (목적)</h2>
                        <p>
                            본 약관은 CertFinder(이하 '회사')가 운영하는 웹사이트 및 서비스의 이용조건 및 절차, 회사와 회원 사이의 권리, 의무 및 책임사항 등을 규정함을 목적으로 합니다.
                        </p>
                    </section>

                    <section className="space-y-4">
                        <h2 className="text-xl font-bold text-white">제 2 조 (제공 서비스)</h2>
                        <p>회사는 회원에게 다음과 같은 서비스를 제공합니다.</p>
                        <ul className="list-disc pl-6 space-y-2">
                            <li>국가자격증 정보 조회 및 분석 데이터</li>
                            <li>사용자 맞춤형 자격증 및 직무 추천</li>
                            <li>관심 자격증 저장 및 관리 기능</li>
                        </ul>
                    </section>

                    <section className="space-y-4 text-amber-400/80">
                        <h2 className="text-xl font-bold text-white">제 3 조 (면책 조항)</h2>
                        <p>
                            본 서비스에서 제공하는 모든 데이터(합격률, 난이도 등)는 공공 데이터 포털 및 관련 기관의 자료를 기반으로 가공된 정보이며, 실제 시험 결과나 최신 변경 사항과 차이가 있을 수 있습니다. 회사는 정보의 정확성이나 신뢰성에 대해 보증하지 않으며, 이용자가 본 정보를 신뢰하여 발생한 결과에 대해 책임을 지지 않습니다.
                        </p>
                    </section>

                    <p className="text-sm text-slate-500 pt-8">
                        공고일자: 2026년 2월 23일<br />
                        시행일자: 2026년 2월 23일
                    </p>
                </div>
            </div>
        </div>
    );
}


import { ChevronLeft, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useRouter } from '@/lib/router';

export function PrivacyPolicyPage() {
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
                    <div className="p-3 bg-blue-600/10 rounded-2xl border border-blue-500/20">
                        <Shield className="w-8 h-8 text-blue-400" />
                    </div>
                    <h1 className="text-3xl font-black text-white">개인정보 처리방침</h1>
                </div>

                <div className="space-y-8 text-slate-300 leading-relaxed">
                    <section className="space-y-4">
                        <h2 className="text-xl font-bold text-white">1. 개인정보의 수집 및 이용 목적</h2>
                        <p>
                            CertFinder(이하 '회사')는 다음의 목적을 위하여 개인정보를 처리합니다. 처리하고 있는 개인정보는 다음의 목적 이외의 용도로는 이용되지 않으며, 이용 목적이 변경되는 경우에는 별도의 동의를 받는 등 필요한 조치를 이행할 예정입니다.
                        </p>
                        <ul className="list-disc pl-6 space-y-2">
                            <li>회원 가입 및 관리: 회원 가입 의사 확인, 서비스 제공에 따른 본인 식별·인증, 회원자격 유지·관리, 서비스 부정 이용 방지</li>
                            <li>서비스 제공: 자격증 맞춤 추천, 직무 매칭 분석, 관심 자격증 관리</li>
                            <li>마케팅 및 광고: 신규 서비스 개발 및 맞춤 서비스 제공, 통계적 특성에 따른 서비스 제공 및 광고 게재</li>
                        </ul> section
                    </section>

                    <section className="space-y-4">
                        <h2 className="text-xl font-bold text-white">2. 수집하는 개인정보의 항목</h2>
                        <p>회사는 회원가입 및 서비스 제공을 위해 아래와 같은 개인정보를 수집하고 있습니다.</p>
                        <ul className="list-disc pl-6 space-y-2">
                            <li>필수 항목: 이메일 주소, 비밀번호, 닉네임, 전공 정보</li>
                            <li>선택 항목: 이름, 생년월일, 상세 관심 분야</li>
                            <li>자동 수집 항목: IP 주소, 쿠키, 서비스 이용 기록, 기기 정보</li>
                        </ul>
                    </section>

                    <section className="space-y-4">
                        <h2 className="text-xl font-bold text-white">3. 개인정보의 보유 및 이용 기간</h2>
                        <p>
                            회사는 법령에 따른 개인정보 보유·이용기간 또는 정보주체로부터 개인정보를 수집 시에 동의 받은 개인정보 보유·이용기간 내에서 개인정보를 처리·보유합니다.
                        </p>
                        <ul className="list-disc pl-6 space-y-2">
                            <li>회원 탈퇴 시까지 (단, 법령에 의해 보존해야 하는 경우 해당 기간까지 보관)</li>
                        </ul>
                    </section>

                    <section className="space-y-4 border-t border-slate-800 pt-8">
                        <h2 className="text-xl font-bold text-white">4. 구글 애드센스 및 쿠키 이용</h2>
                        <p>
                            본 서비스는 구글(Google)에서 제공하는 웹 분석 서비스 및 광고 게재 서비스(애드센스)를 이용할 수 있습니다. 구글은 사용자의 브라우저에 쿠키를 저장하여 사용자의 방문 기록을 분석하고 맞춤형 광고를 제공합니다. 사용자는 브라우저 설정을 통해 쿠키 저장을 거부할 수 있습니다.
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

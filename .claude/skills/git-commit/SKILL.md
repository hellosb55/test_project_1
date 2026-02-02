---
name: git-commit
description: Git commit 자동화 - 문서 업데이트, 변경사항 커밋, 푸시를 자동으로 수행합니다
---

# Git Commit 자동화

사용자가 git commit을 요청하면 아래 단계를 순차적으로 수행합니다.

## 실행 단계

### Step 1: 문서 최신화
`./docs/plan.md`와 `./docs/progress.md` 파일을 최신 상태로 업데이트합니다.

**작업 내용:**
- 완료된 작업에 체크박스 표시 (✅ 또는 `[x]`)
- 진행 중인 작업 상태 업데이트
- 새로 추가된 작업 반영
- 전체 진행률 업데이트

**예시:**
```markdown
- [x] 알림 시스템 구현
- [x] 테스트 작성 및 검증
- [ ] REST API 개발 (다음 단계)
```

### Step 2: Git Add 수행
현재 세션에서 변경된 파일들만 스테이징합니다.

**작업 내용:**
1. `git status`로 변경된 파일 확인
2. 관련 파일들을 개별적으로 추가:
   ```bash
   git add <변경된 파일들>
   ```
3. 민감한 파일(`.env`, `credentials.json` 등) 제외
4. `git status`로 스테이징 상태 확인

**주의사항:**
- `git add .` 또는 `git add -A` 사용 금지 (민감 파일 방지)
- 파일별로 명시적으로 추가

### Step 3: 커밋 메시지 작성
Git branch 전략과 컨벤션을 따라 자세한 커밋 메시지를 작성합니다.

**커밋 메시지 형식:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type 종류:**
- `feat`: 새로운 기능 추가
- `fix`: 버그 수정
- `docs`: 문서 수정
- `style`: 코드 포맷팅, 세미콜론 누락 등
- `refactor`: 코드 리팩토링
- `test`: 테스트 코드 추가/수정
- `chore`: 빌드 업무, 패키지 매니저 수정 등

**작성 예시:**
```bash
git commit -m "$(cat <<'EOF'
feat(alerts): Implement alerting system with multi-channel support

Added comprehensive alerting system:
- Alert rule engine with threshold evaluation
- SQLite storage for alert history
- Email, Slack, and Webhook notification channels
- Alert state management (triggered -> active -> resolved)
- Duration tracking and cooldown periods

Performance impact:
- CPU: +0.2-0.3%
- Memory: +10-15 MB

Tests: 17/17 passed

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

**필수 포함 사항:**
- 변경사항 요약 (무엇을, 왜)
- 주요 구현 내용 (bullet points)
- 성능/테스트 결과 (해당되는 경우)
- Co-Authored-By 태그

### Step 4: Git Push
원격 저장소에 변경사항을 푸시합니다.

**작업 내용:**
1. 현재 브랜치 확인
2. 원격 브랜치 설정 확인
3. Push 수행:
   ```bash
   git push origin <branch-name>
   ```
   또는 업스트림이 설정된 경우:
   ```bash
   git push
   ```

**안전 체크:**
- `main`/`master` 브랜치에 force push 금지
- 푸시 전 원격 변경사항 확인 권장

## 사용 예시

### 명시적 호출
```
/git-commit
```

### 자연어 요청
```
프로젝트를 git에 커밋해주세요
알림 시스템 구현을 커밋하고 푸시해줘
변경사항을 git에 올려줘
```

## 에러 처리

### Pre-commit Hook 실패
- 문제 수정 후 **새로운 커밋** 생성 (--amend 사용 금지)
- 파일 재스테이징 후 다시 커밋

### Push 충돌
- `git pull --rebase` 권장
- 충돌 해결 후 다시 푸시

### 민감 파일 포함
- `.gitignore` 확인
- 이미 스테이징된 경우 `git reset HEAD <file>` 사용

## 제외 대상

다음 파일들은 절대 커밋하지 않습니다:
- `.env`, `.env.local`
- `credentials.json`, `secrets.yaml`
- `*.key`, `*.pem`
- `data/*.db` (선택적)
- `__pycache__/`, `*.pyc`
- `.vscode/`, `.idea/`

## 검증

커밋 후 다음을 확인합니다:
1. `git log -1` - 커밋 메시지 확인
2. `git show --stat` - 변경된 파일 목록 확인
3. 원격 저장소에서 커밋 확인

## 참고사항

- 커밋은 논리적 단위로 분리 (한 커밋 = 한 가지 변경사항)
- 큰 작업은 여러 커밋으로 나누기
- 커밋 전 로컬 테스트 완료 확인
- 문서 업데이트는 코드 변경과 함께 커밋

"use client";

import { User } from "lucide-react";
import { useEffect, useMemo, useState, type ComponentProps } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { avatarSeedFor, buildAvatarUrl, profileInitials, type AvatarStyle } from "@/lib/avatar";
import type { AuthProfile } from "@/lib/auth";
import { cn } from "@/lib/utils";

export type UserAvatarProps = ComponentProps<typeof Avatar> & {
  profile?: AuthProfile | null;
  style?: AvatarStyle;
  seed?: string | null;
  backgroundColor?: string | null;
  size?: number;
  /** Approved extension names; the shorter names remain supported as aliases. */
  avatarStyle?: AvatarStyle;
  avatarSeed?: string | null;
  avatarColor?: string | null;
};

export default function UserAvatar({
  profile = null,
  style,
  seed,
  backgroundColor,
  size,
  avatarStyle,
  avatarSeed,
  avatarColor,
  className,
  ...props
}: UserAvatarProps) {
  const identity = useMemo(
    () => profile?.avatarSeed?.trim() || avatarSeed?.trim() || seed?.trim() || avatarSeedFor(profile),
    [avatarSeed, profile, seed],
  );
  const resolvedStyle = (profile?.avatarStyle as AvatarStyle | null | undefined) ?? avatarStyle ?? style;
  const resolvedColor = profile?.avatarColor ?? avatarColor ?? backgroundColor;
  const src = identity ? buildAvatarUrl({ seed: identity, style: resolvedStyle, backgroundColor: resolvedColor, size }) : null;
  const [errorSrc, setErrorSrc] = useState<string | null>(null);

  useEffect(() => {
    if (errorSrc && errorSrc !== src) setErrorSrc(null);
  }, [errorSrc, src]);

  const imageError = Boolean(src && errorSrc === src);
  const initials = profileInitials(profile);
  return (
    <Avatar className={cn("h-9 w-9", className)} {...props}>
      {src && !imageError ? (
        <AvatarImage
          src={src}
          alt={profile?.name?.trim() || profile?.email?.trim() || "Generated account avatar"}
          onError={() => setErrorSrc(src)}
        />
      ) : null}
      {!src || imageError ? (
        <AvatarFallback className="bg-teal-500 text-sm font-bold text-teal-950">
          {initials ? initials : <User className="size-4" aria-label="Guest account" />}
        </AvatarFallback>
      ) : null}
    </Avatar>
  );
}
